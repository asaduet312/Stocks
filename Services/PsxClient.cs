using System.Globalization;
using System.Text.Json;
using System.Text.RegularExpressions;
using HtmlAgilityPack;
using StocksDotNet.Models;

namespace StocksDotNet.Services;

public class PsxClient
{
    public const string BaseUrl = "https://dps.psx.com.pk";

    private static readonly Dictionary<string, string> ColumnMap = new(StringComparer.Ordinal)
    {
        ["SYMBOL"] = "symbol",
        ["Symbol"] = "symbol",
        ["LDCP"] = "ldcp",
        ["CURRENT"] = "current",
        ["Current"] = "current",
        ["CHANGE"] = "change",
        ["CHANGE (%)"] = "change_pct",
        ["% Change"] = "change_pct",
        ["VOLUME"] = "volume",
    };

    private readonly HttpClient _http;

    public PsxClient(HttpClient http)
    {
        _http = http;
        _http.Timeout = TimeSpan.FromSeconds(30);
        if (!_http.DefaultRequestHeaders.UserAgent.Any())
        {
            _http.DefaultRequestHeaders.TryAddWithoutValidation(
                "User-Agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36");
            _http.DefaultRequestHeaders.TryAddWithoutValidation(
                "Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8");
            _http.DefaultRequestHeaders.TryAddWithoutValidation("Accept-Language", "en-US,en;q=0.5");
            _http.DefaultRequestHeaders.TryAddWithoutValidation("Referer", "https://dps.psx.com.pk/");
            _http.DefaultRequestHeaders.TryAddWithoutValidation("X-Requested-With", "XMLHttpRequest");
        }
    }

    public static TimeZoneInfo KarachiTz { get; } = ResolveKarachiTz();

    public static DateTimeOffset NowKarachi() =>
        TimeZoneInfo.ConvertTime(DateTimeOffset.UtcNow, KarachiTz);

    public async Task<Dictionary<string, Quote>> LoadBoardQuotesAsync()
    {
        var html = await GetStringWithRetryAsync($"{BaseUrl}/trading-board/REG/main");
        var rows = ParseHtmlTable(html);
        var quotes = new Dictionary<string, Quote>(StringComparer.OrdinalIgnoreCase);

        foreach (var row in rows)
        {
            var sym = Get(row, "symbol")?.Trim().ToUpperInvariant();
            if (string.IsNullOrEmpty(sym)) continue;

            var current = CoerceNumeric(Get(row, "current"));
            var ldcp = CoerceNumeric(Get(row, "ldcp"));
            var change = CoerceNumeric(Get(row, "change"));
            var changePct = CoerceNumeric(Get(row, "change_pct"));
            var volume = CoerceNumeric(Get(row, "volume"));

            double? price = null;
            if (current.HasValue) price = current;
            else if (ldcp.HasValue && change.HasValue) price = ldcp.Value + change.Value;
            else if (ldcp.HasValue) price = ldcp;

            if (!changePct.HasValue && ldcp.HasValue && ldcp.Value != 0 && change.HasValue)
                changePct = change.Value / ldcp.Value * 100;

            quotes[sym] = new Quote
            {
                Price = price,
                ChangePct = changePct,
                Volume = volume,
            };
        }

        return quotes;
    }

    /// <summary>
    /// Loads day high / day low (and quote fields when present) from the PSX company page REG panel.
    /// </summary>
    public async Task<Quote?> FetchCompanyQuoteAsync(string symbol)
    {
        var sym = symbol.Trim().ToUpperInvariant();
        if (string.IsNullOrEmpty(sym)) return null;

        try
        {
            var html = await GetStringWithRetryAsync($"{BaseUrl}/company/{sym}");
            var doc = new HtmlDocument();
            doc.LoadHtml(html);

            // Company pages include REG / FUT / CSF / ODL panels, each with its own High/Low.
            // Always read the regular-market (REG) panel only.
            var regPanel = doc.DocumentNode.SelectSingleNode(
                "//div[contains(@class,'tabs__panel') and @data-name='REG']")
                ?? doc.DocumentNode;

            double? dayHigh = null;
            double? dayLow = null;
            double? volume = null;

            // Prefer official DAY RANGE attributes from the REG panel.
            var dayRange = regPanel.SelectSingleNode(
                ".//div[contains(@class,'stats_label') and contains(normalize-space(.),'DAY RANGE')]"
                + "/following-sibling::div[contains(@class,'stats_value')]"
                + "//div[contains(@class,'numRange')]");
            if (dayRange != null)
            {
                dayLow = PositiveOrNull(CoerceNumeric(dayRange.GetAttributeValue("data-low", "")));
                dayHigh = PositiveOrNull(CoerceNumeric(dayRange.GetAttributeValue("data-high", "")));
            }

            // Fallback to REG Open/High/Low/Volume stats.
            var statsItems = regPanel.SelectNodes(".//div[contains(@class,'stats_item')]");
            if (statsItems != null)
            {
                foreach (var item in statsItems)
                {
                    var label = HtmlEntity.DeEntitize(
                        item.SelectSingleNode("./div[contains(@class,'stats_label')]")?.InnerText ?? "").Trim();
                    var valueNode = item.SelectSingleNode("./div[contains(@class,'stats_value')]");
                    if (valueNode == null) continue;

                    // Use direct text (exclude nested widgets like numRange).
                    var valueText = HtmlEntity.DeEntitize(
                        string.Concat(valueNode.ChildNodes
                            .Where(n => n.NodeType == HtmlNodeType.Text)
                            .Select(n => n.InnerText))).Trim();
                    if (string.IsNullOrWhiteSpace(valueText))
                        valueText = HtmlEntity.DeEntitize(valueNode.InnerText).Trim();

                    if (label.Equals("High", StringComparison.OrdinalIgnoreCase))
                        dayHigh ??= PositiveOrNull(CoerceNumeric(valueText));
                    else if (label.Equals("Low", StringComparison.OrdinalIgnoreCase))
                        dayLow ??= PositiveOrNull(CoerceNumeric(valueText));
                    else if (label.Equals("Volume", StringComparison.OrdinalIgnoreCase))
                        volume ??= CoerceNumeric(valueText);
                }
            }

            var priceText = HtmlEntity.DeEntitize(
                doc.DocumentNode.SelectSingleNode("//div[contains(@class,'quote__close')]")?.InnerText ?? "");
            var price = CoerceNumeric(priceText);

            var pctText = HtmlEntity.DeEntitize(
                doc.DocumentNode.SelectSingleNode("//div[contains(@class,'change__percent')]")?.InnerText ?? "");
            var changePct = CoerceNumeric(pctText);

            if (dayLow.HasValue && dayHigh.HasValue && dayLow.Value > dayHigh.Value)
                (dayLow, dayHigh) = (dayHigh, dayLow);

            if (price is null && dayHigh is null && dayLow is null)
                return null;

            return new Quote
            {
                Price = price,
                ChangePct = changePct,
                Volume = volume,
                DayHigh = dayHigh,
                DayLow = dayLow,
            };
        }
        catch
        {
            return null;
        }
    }

    private static double? PositiveOrNull(double? value) =>
        value is > 0 ? value : null;

    public async Task<List<Tick>> FetchIntradayTicksAsync(string symbol)
    {
        var sym = symbol.Trim().ToUpperInvariant();
        var url = $"{BaseUrl}/timeseries/int/{sym}";
        try
        {
            using var resp = await _http.GetAsync(url);
            resp.EnsureSuccessStatusCode();
            await using var stream = await resp.Content.ReadAsStreamAsync();
            using var doc = await JsonDocument.ParseAsync(stream);
            if (!doc.RootElement.TryGetProperty("data", out var data) || data.ValueKind != JsonValueKind.Array)
                return [];

            var ticks = new List<Tick>();
            foreach (var item in data.EnumerateArray())
            {
                if (item.ValueKind != JsonValueKind.Array || item.GetArrayLength() < 2) continue;
                if (!TryNumber(item[0], out var ts) || !TryNumber(item[1], out var price)) continue;
                var vol = item.GetArrayLength() > 2 && TryNumber(item[2], out var v) ? v : 0;
                var utc = DateTimeOffset.FromUnixTimeSeconds((long)ts);
                ticks.Add(new Tick
                {
                    Timestamp = (long)ts,
                    Price = price,
                    Volume = vol,
                    KarachiTime = TimeZoneInfo.ConvertTime(utc, KarachiTz),
                });
            }

            ticks.Sort((a, b) => a.Timestamp.CompareTo(b.Timestamp));
            return ticks;
        }
        catch
        {
            return [];
        }
    }

    private async Task<string> GetStringWithRetryAsync(string url)
    {
        Exception? last = null;
        for (var attempt = 0; attempt < 3; attempt++)
        {
            try
            {
                if (attempt > 0)
                    await Task.Delay(attempt == 1 ? 1000 : 2000);
                return await _http.GetStringAsync(url);
            }
            catch (Exception ex)
            {
                last = ex;
            }
        }
        throw last ?? new HttpRequestException("PSX request failed");
    }

    private static List<Dictionary<string, string>> ParseHtmlTable(string html)
    {
        var doc = new HtmlDocument();
        doc.LoadHtml(html);
        var table = doc.DocumentNode.SelectSingleNode("//table");
        if (table == null) return [];

        var headers = table.SelectNodes(".//th")?
            .Select(th =>
            {
                var raw = HtmlEntity.DeEntitize(th.InnerText).Trim();
                return ColumnMap.TryGetValue(raw, out var mapped)
                    ? mapped
                    : NormalizeColumnName(raw);
            })
            .ToList() ?? [];

        if (headers.Count == 0) return [];

        var trNodes = table.SelectNodes(".//tbody/tr") ?? table.SelectNodes(".//tr");
        if (trNodes == null) return [];

        var rows = new List<Dictionary<string, string>>();
        foreach (var tr in trNodes)
        {
            var cells = tr.SelectNodes("./td");
            if (cells == null || cells.Count == 0) continue;
            var row = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            for (var i = 0; i < Math.Min(headers.Count, cells.Count); i++)
                row[headers[i]] = HtmlEntity.DeEntitize(cells[i].InnerText).Trim();
            rows.Add(row);
        }
        return rows;
    }

    private static string? Get(Dictionary<string, string> row, string key) =>
        row.TryGetValue(key, out var v) ? v : null;

    public static double? CoerceNumeric(string? value)
    {
        if (string.IsNullOrWhiteSpace(value)) return null;
        var cleaned = value.Replace(",", "").Replace("%", "").Replace("PKR", "", StringComparison.OrdinalIgnoreCase).Trim();
        return double.TryParse(cleaned, NumberStyles.Float, CultureInfo.InvariantCulture, out var n) ? n : null;
    }

    private static string NormalizeColumnName(string name)
    {
        name = name.Trim().ToLowerInvariant().Replace(' ', '_');
        name = Regex.Replace(name, @"[^\w]", "_");
        name = Regex.Replace(name, "_+", "_").Trim('_');
        return name;
    }

    private static bool TryNumber(JsonElement el, out double value)
    {
        value = 0;
        if (el.ValueKind == JsonValueKind.Number)
        {
            value = el.GetDouble();
            return true;
        }
        if (el.ValueKind == JsonValueKind.String)
            return double.TryParse(el.GetString(), NumberStyles.Float, CultureInfo.InvariantCulture, out value);
        return false;
    }

    private static TimeZoneInfo ResolveKarachiTz()
    {
        foreach (var id in new[] { "Asia/Karachi", "Pakistan Standard Time" })
        {
            try { return TimeZoneInfo.FindSystemTimeZoneById(id); }
            catch (TimeZoneNotFoundException) { }
            catch (InvalidTimeZoneException) { }
        }
        return TimeZoneInfo.CreateCustomTimeZone("Asia/Karachi", TimeSpan.FromHours(5), "Asia/Karachi", "Asia/Karachi");
    }
}
