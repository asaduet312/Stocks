using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using StocksDotNet.Models;
using StocksDotNet.Services;

namespace StocksDotNet.Pages;

public class NearToLowModel : PageModel
{
    private readonly MarketService _market;
    private readonly WatchlistService _watchlists;

    public NearToLowModel(MarketService market, WatchlistService watchlists)
    {
        _market = market;
        _watchlists = watchlists;
    }

    public List<NearToLowRow> Rows { get; private set; } = [];

    public async Task OnGetAsync()
    {
        await LoadAsync();
    }

    public async Task<IActionResult> OnPostRefreshAsync()
    {
        await LoadAsync();
        return Page();
    }

    private async Task LoadAsync()
    {
        var watchlist = _watchlists.LoadCommonWatchlist();
        var symbols = watchlist.Where(s => s.Included).Select(s => s.Symbol);
        Rows = await _market.LoadNearToLowListAsync(symbols);
    }
}
