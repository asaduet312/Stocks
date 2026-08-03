using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using StocksDotNet.Models;
using StocksDotNet.Services;

namespace StocksDotNet.Pages;

public class TenMinBreakoutModel : PageModel
{
    private readonly MarketService _market;
    private readonly WatchlistService _watchlists;

    public TenMinBreakoutModel(MarketService market, WatchlistService watchlists)
    {
        _market = market;
        _watchlists = watchlists;
    }

    [BindProperty]
    public double MinChangePct { get; set; } = 2.0;

    [BindProperty]
    public string? NewSymbol { get; set; }

    public List<StockItem> Watchlist { get; private set; } = [];
    public List<BreakoutRow> Rows { get; private set; } = [];
    public string? Message { get; private set; }

    public async Task OnGetAsync(double? minChangePct)
    {
        if (minChangePct.HasValue) MinChangePct = minChangePct.Value;
        await LoadAsync();
    }

    public async Task<IActionResult> OnPostRefreshAsync()
    {
        await LoadAsync();
        return Page();
    }

    public async Task<IActionResult> OnPostAddAsync()
    {
        var stocks = _watchlists.LoadTenMinWatchlist();
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
            _watchlists.SaveTenMinWatchlist(stocks);
        }
        NewSymbol = "";
        await LoadAsync();
        return Page();
    }

    public async Task<IActionResult> OnPostToggleAsync(string symbol, bool included)
    {
        var stocks = _watchlists.LoadTenMinWatchlist();
        var item = stocks.FirstOrDefault(s => s.Symbol.Equals(symbol, StringComparison.OrdinalIgnoreCase));
        if (item != null)
        {
            item.Included = included;
            _watchlists.SaveTenMinWatchlist(stocks);
        }
        await LoadAsync();
        return Page();
    }

    public async Task<IActionResult> OnPostRemoveAsync(string symbol)
    {
        var stocks = _watchlists.LoadTenMinWatchlist()
            .Where(s => !s.Symbol.Equals(symbol, StringComparison.OrdinalIgnoreCase))
            .ToList();
        _watchlists.SaveTenMinWatchlist(stocks);
        await LoadAsync();
        return Page();
    }

    private async Task LoadAsync()
    {
        Watchlist = _watchlists.LoadTenMinWatchlist();
        var symbols = Watchlist.Where(s => s.Included).Select(s => s.Symbol);
        Rows = await _market.LoadTenMinBreakoutListAsync(symbols, MinChangePct);
    }
}
