using StocksDotNet.Models;

namespace StocksDotNet.Services;

/// <summary>
/// Exact port of Python data/market.py breakout + candle logic.
/// </summary>
public class MarketService
{
    private readonly PsxClient _psx;

    public MarketService(PsxClient psx) => _psx = psx;

    public async Task<List<BreakoutRow>> LoadTenMinBreakoutListAsync(
        IEnumerable<string> symbols,
        double minChangePct = 2.0)
    {
        var symbolList = symbols
            .Select(s => s.Trim().ToUpperInvariant())
            .Where(s => s.Length > 0)
            .Distinct()
            .ToList();
        if (symbolList.Count == 0) return [];

        var quotes = await _psx.LoadBoardQuotesAsync();
        var candidates = new List<(string Sym, Quote Quote)>();
        foreach (var sym in symbolList)
        {
            if (!quotes.TryGetValue(sym, out var quote)) continue;
            if (quote.ChangePct is null || quote.ChangePct.Value < minChangePct) continue;
            candidates.Add((sym, quote));
        }
        if (candidates.Count == 0) return [];

        var workers = Math.Min(8, Math.Max(1, candidates.Count));
        using var gate = new SemaphoreSlim(workers);
        var tasks = candidates.Select(async c =>
        {
            await gate.WaitAsync();
            try { return await EvaluateBreakoutRowAsync(c.Sym, c.Quote); }
            finally { gate.Release(); }
        });

        var results = await Task.WhenAll(tasks);
        return results
            .Where(r => r != null)
            .Cast<BreakoutRow>()
            .GroupBy(r => r.Symbol, StringComparer.OrdinalIgnoreCase)
            .Select(g => g.Last())
            .OrderBy(r => r.PriceDistance)
            .ThenByDescending(r => r.ChangePct)
            .ToList();
    }

    public async Task<List<NearToLowRow>> LoadNearToLowListAsync(IEnumerable<string> symbols)
    {
        var symbolList = symbols
            .Select(s => s.Trim().ToUpperInvariant())
            .Where(s => s.Length > 0)
            .Distinct()
            .ToList();
        if (symbolList.Count == 0) return [];

        var boardQuotes = await _psx.LoadBoardQuotesAsync();

        var workers = Math.Min(8, Math.Max(1, symbolList.Count));
        using var gate = new SemaphoreSlim(workers);
        var tasks = symbolList.Select(async sym =>
        {
            await gate.WaitAsync();
            try { return await BuildNearToLowRowAsync(sym, boardQuotes); }
            finally { gate.Release(); }
        });

        var results = await Task.WhenAll(tasks);
        return results
            .Where(r => r != null)
            .Cast<NearToLowRow>()
            .OrderBy(r => r.LowDistance)
            .ThenBy(r => r.Symbol, StringComparer.OrdinalIgnoreCase)
            .ToList();
    }

    private async Task<NearToLowRow?> BuildNearToLowRowAsync(
        string symbol,
        Dictionary<string, Quote> boardQuotes)
    {
        boardQuotes.TryGetValue(symbol, out var board);
        var company = await _psx.FetchCompanyQuoteAsync(symbol);

        var price = company?.Price ?? board?.Price;
        var changePct = company?.ChangePct ?? board?.ChangePct;
        var volume = company?.Volume ?? board?.Volume;
        var dayLow = company?.DayLow is > 0 ? company.DayLow : null;
        var dayHigh = company?.DayHigh is > 0 ? company.DayHigh : null;

        // Fallback: derive day range from today's intraday ticks when company page lacks it.
        if (dayLow is null || dayHigh is null)
        {
            var ticks = await _psx.FetchIntradayTicksAsync(symbol);
            var today = PsxClient.NowKarachi().Date;
            var todayPrices = ticks
                .Where(t => t.KarachiTime.Date == today && t.Price > 0)
                .Select(t => t.Price)
                .ToList();
            if (todayPrices.Count > 0)
            {
                dayLow ??= todayPrices.Min();
                dayHigh ??= todayPrices.Max();
            }
        }

        if (price is null || dayLow is null || dayHigh is null)
            return null;

        if (dayLow.Value > dayHigh.Value)
            (dayLow, dayHigh) = (dayHigh, dayLow);

        return new NearToLowRow
        {
            Symbol = symbol,
            CurrentPrice = price.Value,
            ChangePct = changePct ?? 0,
            DayLow = dayLow.Value,
            LowDistance = price.Value - dayLow.Value,
            DayHigh = dayHigh.Value,
            HighDistance = dayHigh.Value - price.Value,
            Volume = volume.HasValue ? volume.Value / 1_000_000.0 : null,
        };
    }

    public async Task<List<CandleBar>> PrepareLastAndCurrentDayBarsAsync(string symbol)
    {
        const int intervalMinutes = 5;
        var ticks = await _psx.FetchIntradayTicksAsync(symbol);
        if (ticks.Count == 0) return [];

        var sessions = ticks
            .Select(t => t.KarachiTime.Date)
            .Distinct()
            .OrderBy(d => d)
            .ToList();
        if (sessions.Count == 0) return [];

        var selected = sessions.TakeLast(2).ToHashSet();
        var filtered = ticks.Where(t => selected.Contains(t.KarachiTime.Date)).ToList();
        if (filtered.Count == 0) return [];

        var bars = ResampleOhlcv(filtered, intervalMinutes);
        var rows = new List<CandleBar>();
        foreach (var bar in bars)
        {
            var (o, h, l, c) = NormalizeOhlc(bar.Open, bar.High, bar.Low, bar.Close);
            rows.Add(new CandleBar
            {
                Timestamp = bar.Start.ToUnixTimeSeconds(),
                Open = o,
                High = h,
                Low = l,
                Close = c,
                Volume = bar.Volume,
            });
        }
        return rows;
    }

    private async Task<BreakoutRow?> EvaluateBreakoutRowAsync(string symbol, Quote quote)
    {
        if (quote.Price is null || quote.ChangePct is null) return null;

        var ticks = await _psx.FetchIntradayTicksAsync(symbol);
        var candle = FirstCompleted10mCandle(ticks);
        if (candle is null) return null;
        if (candle.Close <= candle.Open) return null;
        if (quote.Price.Value <= candle.High) return null;

        var breakoutPrice = candle.High;
        var breakoutTime = LastBreakoutTimeAboveLevel(ticks, breakoutPrice, candle.Start);
        if (breakoutTime is null) return null;

        return new BreakoutRow
        {
            Symbol = symbol,
            CurrentPrice = quote.Price.Value,
            BreakoutTime = breakoutTime,
            PriceDistance = quote.Price.Value - breakoutPrice,
            ChangePct = quote.ChangePct.Value,
            Volume = quote.Volume.HasValue ? quote.Volume.Value / 1_000_000.0 : null,
            First10MinuteHigh = breakoutPrice,
        };
    }

    private static Candle10m? FirstCompleted10mCandle(List<Tick> ticks)
    {
        if (ticks.Count == 0) return null;

        var now = PsxClient.NowKarachi();
        var today = now.Date;
        var todayTicks = ticks.Where(t => t.KarachiTime.Date == today).ToList();
        if (todayTicks.Count == 0) return null;

        var bars = ResampleOhlc(todayTicks, 10);
        if (bars.Count == 0) return null;

        var first = bars[0];
        if (now < first.Start.AddMinutes(10)) return null;

        return new Candle10m
        {
            Open = first.Open,
            High = first.High,
            Close = first.Close,
            Start = first.Start,
        };
    }

    private static string? LastBreakoutTimeAboveLevel(
        List<Tick> ticks,
        double level,
        DateTimeOffset firstCandleStart)
    {
        if (ticks.Count == 0) return null;

        var today = PsxClient.NowKarachi().Date;
        var afterFirst10m = firstCandleStart.AddMinutes(10);
        var eligible = ticks
            .Where(t => t.KarachiTime.Date == today && t.KarachiTime >= afterFirst10m)
            .ToList();
        if (eligible.Count == 0) return null;

        var above = eligible.Select(t => t.Price > level).ToList();
        if (!above[^1]) return null;

        var lastCross = -1;
        for (var i = 0; i < above.Count; i++)
        {
            var prev = i == 0 ? false : above[i - 1];
            if (above[i] && !prev) lastCross = i;
        }

        var ts = lastCross >= 0 ? eligible[lastCross].KarachiTime : eligible[0].KarachiTime;
        return ts.ToString("HH:mm:ss");
    }

    private static List<OhlcBar> ResampleOhlc(List<Tick> ticks, int intervalMinutes)
    {
        var groups = ticks
            .GroupBy(t => FloorBucket(t.KarachiTime, intervalMinutes))
            .OrderBy(g => g.Key);

        var bars = new List<OhlcBar>();
        foreach (var g in groups)
        {
            var prices = g.Select(t => t.Price).ToList();
            if (prices.Count == 0) continue;
            bars.Add(new OhlcBar
            {
                Start = g.Key,
                Open = prices[0],
                High = prices.Max(),
                Low = prices.Min(),
                Close = prices[^1],
                Volume = 0,
            });
        }
        return bars;
    }

    private static List<OhlcBar> ResampleOhlcv(List<Tick> ticks, int intervalMinutes)
    {
        var groups = ticks
            .GroupBy(t => FloorBucket(t.KarachiTime, intervalMinutes))
            .OrderBy(g => g.Key);

        var bars = new List<OhlcBar>();
        foreach (var g in groups)
        {
            var list = g.ToList();
            if (list.Count == 0) continue;
            bars.Add(new OhlcBar
            {
                Start = g.Key,
                Open = list[0].Price,
                High = list.Max(t => t.Price),
                Low = list.Min(t => t.Price),
                Close = list[^1].Price,
                Volume = list.Sum(t => t.Volume),
            });
        }
        return bars;
    }

    /// <summary>Left-labeled wall-clock bucket, matching pandas resample("Nmin").</summary>
    private static DateTimeOffset FloorBucket(DateTimeOffset dt, int intervalMinutes)
    {
        var minute = dt.Minute / intervalMinutes * intervalMinutes;
        return new DateTimeOffset(dt.Year, dt.Month, dt.Day, dt.Hour, minute, 0, dt.Offset);
    }

    public static (double Open, double High, double Low, double Close) NormalizeOhlc(
        double open, double high, double low, double close)
    {
        high = Math.Max(high, Math.Max(open, close));
        low = Math.Min(low, Math.Min(open, close));
        return (open, high, low, close);
    }

    private sealed class OhlcBar
    {
        public DateTimeOffset Start { get; set; }
        public double Open { get; set; }
        public double High { get; set; }
        public double Low { get; set; }
        public double Close { get; set; }
        public double Volume { get; set; }
    }
}
