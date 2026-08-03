using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using StocksDotNet.Models;
using StocksDotNet.Services;

namespace StocksDotNet.Pages;

public class CommonWatchListSetupModel : PageModel
{
    private readonly WatchlistService _watchlists;

    public CommonWatchListSetupModel(WatchlistService watchlists)
    {
        _watchlists = watchlists;
    }

    [BindProperty]
    public string? NewSymbol { get; set; }

    public List<StockItem> Watchlist { get; private set; } = [];
    public string? Message { get; private set; }

    public void OnGet()
    {
        Load();
    }

    public IActionResult OnPostAdd()
    {
        var stocks = _watchlists.LoadCommonWatchlist();
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
            _watchlists.SaveCommonWatchlist(stocks);
        }
        NewSymbol = "";
        Load();
        return Page();
    }

    public IActionResult OnPostRemove(string symbol)
    {
        var stocks = _watchlists.LoadCommonWatchlist()
            .Where(s => !s.Symbol.Equals(symbol, StringComparison.OrdinalIgnoreCase))
            .ToList();
        _watchlists.SaveCommonWatchlist(stocks);
        Load();
        return Page();
    }

    private void Load()
    {
        Watchlist = _watchlists.LoadCommonWatchlist();
    }
}
