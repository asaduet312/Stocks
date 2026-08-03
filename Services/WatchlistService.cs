using System.Text.Json;
using StocksDotNet.Models;

namespace StocksDotNet.Services;

public class WatchlistService
{
    public static readonly Dictionary<string, string> NameHints = new(StringComparer.OrdinalIgnoreCase)
    {
        ["PRL"] = "Pakistan Refinery",
        ["BIPL"] = "Biafo Industries",
        ["POWER"] = "Power Cement",
        ["LOADS"] = "Loads Limited",
    };

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
    };

    private readonly string _dataDir;
    private readonly string _stocksListPath;
    private readonly string _tenMinPath;
    private readonly string _commonPath;

    public WatchlistService(IWebHostEnvironment env)
    {
        _dataDir = Path.Combine(env.ContentRootPath, "Data");
        Directory.CreateDirectory(_dataDir);
        _stocksListPath = Path.Combine(_dataDir, "StocksList.json");
        _tenMinPath = Path.Combine(_dataDir, "10MinutesWatchlist.json");
        _commonPath = Path.Combine(_dataDir, "CommonWatchList.json");
    }

    public List<StockItem> LoadStocksList()
    {
        var stocks = Read(_stocksListPath);
        if (stocks == null)
        {
            stocks = DefaultStocks();
            SaveStocksList(stocks);
        }
        return stocks;
    }

    public void SaveStocksList(List<StockItem> stocks) => Write(_stocksListPath, stocks);

    public List<StockItem> LoadTenMinWatchlist()
    {
        var stocks = Read(_tenMinPath);
        if (stocks == null)
        {
            stocks = LoadStocksList().Select(s => new StockItem
            {
                Symbol = s.Symbol,
                Name = s.Name,
                Included = s.Included,
            }).ToList();
            SaveTenMinWatchlist(stocks);
        }
        return stocks;
    }

    public void SaveTenMinWatchlist(List<StockItem> stocks) => Write(_tenMinPath, stocks);

    public List<StockItem> LoadCommonWatchlist()
    {
        var stocks = Read(_commonPath);
        if (stocks == null)
        {
            stocks = LoadTenMinWatchlist().Select(s => new StockItem
            {
                Symbol = s.Symbol,
                Name = s.Name,
                Included = s.Included,
            }).ToList();
            SaveCommonWatchlist(stocks);
        }
        return stocks;
    }

    public void SaveCommonWatchlist(List<StockItem> stocks) => Write(_commonPath, stocks);

    public string ResolveName(string symbol) =>
        NameHints.TryGetValue(symbol.Trim().ToUpperInvariant(), out var name) ? name : "";

    private static List<StockItem> DefaultStocks() =>
        NameHints.Select(kv => new StockItem
        {
            Symbol = kv.Key,
            Name = kv.Value,
            Included = true,
        }).ToList();

    private static List<StockItem>? Read(string path)
    {
        if (!File.Exists(path)) return null;
        try
        {
            using var doc = JsonDocument.Parse(File.ReadAllText(path));
            if (!doc.RootElement.TryGetProperty("stocks", out var arr) || arr.ValueKind != JsonValueKind.Array)
                return null;

            var stocks = new List<StockItem>();
            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (var item in arr.EnumerateArray())
            {
                var sym = item.TryGetProperty("symbol", out var s)
                    ? s.GetString()?.Trim().ToUpperInvariant() ?? ""
                    : "";
                if (string.IsNullOrEmpty(sym) || !seen.Add(sym)) continue;
                stocks.Add(new StockItem
                {
                    Symbol = sym,
                    Name = item.TryGetProperty("name", out var n) ? n.GetString()?.Trim() ?? "" : "",
                    Included = !item.TryGetProperty("included", out var inc) || inc.GetBoolean(),
                });
            }
            return stocks.Count == 0 ? null : stocks;
        }
        catch
        {
            return null;
        }
    }

    private static void Write(string path, List<StockItem> stocks)
    {
        var payload = new
        {
            stocks = stocks.Select(s => new
            {
                symbol = s.Symbol,
                name = s.Name ?? "",
                included = s.Included,
            }),
        };
        File.WriteAllText(path, JsonSerializer.Serialize(payload, JsonOptions) + "\n");
    }
}
