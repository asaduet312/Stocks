using System.Text.Json;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using StocksDotNet.Models;
using StocksDotNet.Services;

namespace StocksDotNet.Pages;

public class CandleChartModel : PageModel
{
    private readonly MarketService _market;
    private readonly WatchlistService _watchlists;

    public CandleChartModel(MarketService market, WatchlistService watchlists)
    {
        _market = market;
        _watchlists = watchlists;
    }

    [BindProperty(SupportsGet = true)]
    public string? Symbol { get; set; }

    [BindProperty]
    public string? NewSymbol { get; set; }

    public List<StockItem> Stocks { get; private set; } = [];
    public List<CandleBar> Bars { get; private set; } = [];
    public string SelectedTitle { get; private set; } = "";
    public string? Message { get; private set; }
    public string CandlesJson { get; private set; } = "[]";
    public string VolumesJson { get; private set; } = "[]";

    public async Task OnGetAsync()
    {
        await LoadAsync();
    }

    public async Task<IActionResult> OnGetBarsAsync(string symbol)
    {
        var bars = await _market.PrepareLastAndCurrentDayBarsAsync(symbol);
        var (candles, volumes) = ToChartPayload(bars);
        return new JsonResult(new { candles, volumes, count = bars.Count });
    }

    public async Task<IActionResult> OnPostAddAsync()
    {
        var stocks = _watchlists.LoadStocksList();
        var sym = (NewSymbol ?? "").Trim().ToUpperInvariant();
        if (string.IsNullOrEmpty(sym))
        {
            Message = "Enter a ticker.";
        }
        else if (stocks.Any(s => s.Symbol == sym))
        {
            Message = $"{sym} already listed.";
        }
        else
        {
            stocks.Add(new StockItem
            {
                Symbol = sym,
                Name = _watchlists.ResolveName(sym),
                Included = true,
            });
            _watchlists.SaveStocksList(stocks);
            Symbol = sym;
        }
        NewSymbol = "";
        await LoadAsync();
        return Page();
    }

    public async Task<IActionResult> OnPostSelectAsync(string symbol)
    {
        Symbol = symbol;
        await LoadAsync();
        return Page();
    }

    public async Task<IActionResult> OnPostRemoveAsync(string symbol)
    {
        var stocks = _watchlists.LoadStocksList()
            .Where(s => !s.Symbol.Equals(symbol, StringComparison.OrdinalIgnoreCase))
            .ToList();
        _watchlists.SaveStocksList(stocks);
        if (Symbol != null && Symbol.Equals(symbol, StringComparison.OrdinalIgnoreCase))
            Symbol = stocks.FirstOrDefault()?.Symbol;
        await LoadAsync();
        return Page();
    }

    private async Task LoadAsync()
    {
        Stocks = _watchlists.LoadStocksList();
        if (Stocks.Count == 0)
        {
            SelectedTitle = "";
            Bars = [];
            CandlesJson = "[]";
            VolumesJson = "[]";
            return;
        }

        if (string.IsNullOrWhiteSpace(Symbol) ||
            Stocks.All(s => !s.Symbol.Equals(Symbol, StringComparison.OrdinalIgnoreCase)))
        {
            Symbol = Stocks[0].Symbol;
        }

        Symbol = Symbol!.Trim().ToUpperInvariant();
        var stock = Stocks.First(s => s.Symbol == Symbol);
        SelectedTitle = string.IsNullOrWhiteSpace(stock.Name)
            ? stock.Symbol
            : $"{stock.Symbol} — {stock.Name}";

        Bars = await _market.PrepareLastAndCurrentDayBarsAsync(Symbol);
        var (candles, volumes) = ToChartPayload(Bars);
        CandlesJson = JsonSerializer.Serialize(candles);
        VolumesJson = JsonSerializer.Serialize(volumes);
    }

    private static (List<object> Candles, List<object> Volumes) ToChartPayload(List<CandleBar> bars)
    {
        var candles = new List<object>();
        var volumes = new List<object>();
        foreach (var b in bars.OrderBy(x => x.Timestamp))
        {
            var (o, h, l, c) = MarketService.NormalizeOhlc(b.Open, b.High, b.Low, b.Close);
            var up = c >= o;
            candles.Add(new { time = b.Timestamp, open = o, high = h, low = l, close = c });
            volumes.Add(new
            {
                time = b.Timestamp,
                value = b.Volume,
                color = up ? "rgba(38, 166, 154, 0.55)" : "rgba(239, 83, 80, 0.55)",
            });
        }
        return (candles, volumes);
    }
}
