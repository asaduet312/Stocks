namespace StocksDotNet.Models;

public class StockItem
{
    public string Symbol { get; set; } = "";
    public string Name { get; set; } = "";
    public bool Included { get; set; } = true;
}

public class Quote
{
    public double? Price { get; set; }
    public double? ChangePct { get; set; }
    public double? Volume { get; set; }
    public double? DayHigh { get; set; }
    public double? DayLow { get; set; }
}

public class NearToLowRow
{
    public string Symbol { get; set; } = "";
    public double CurrentPrice { get; set; }
    public double ChangePct { get; set; }
    public double DayLow { get; set; }
    public double LowDistance { get; set; }
    public double DayHigh { get; set; }
    public double HighDistance { get; set; }
    public double? Volume { get; set; }
}

public class Tick
{
    public long Timestamp { get; set; }
    public double Price { get; set; }
    public double Volume { get; set; }
    public DateTimeOffset KarachiTime { get; set; }
}

public class Candle10m
{
    public double Open { get; set; }
    public double High { get; set; }
    public double Close { get; set; }
    public DateTimeOffset Start { get; set; }
}

public class BreakoutRow
{
    public string Symbol { get; set; } = "";
    public double CurrentPrice { get; set; }
    public string BreakoutTime { get; set; } = "";
    public double PriceDistance { get; set; }
    public double ChangePct { get; set; }
    public double? Volume { get; set; }
    public double First10MinuteHigh { get; set; }
}

public class CandleBar
{
    public long Timestamp { get; set; }
    public double Open { get; set; }
    public double High { get; set; }
    public double Low { get; set; }
    public double Close { get; set; }
    public double Volume { get; set; }
}
