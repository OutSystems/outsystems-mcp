---
name: outsystems-charts
description: Catalog of OutSystems Charts blocks (Charts API v2) — column, bar, line, area, pie, donut, scatter, and the supporting addons. Use to pick the right chart block + addons for a spec when the design contains a chart.
---

# OutSystems Charts

Separate Forge component (not core OutSystems UI). Backed by Highcharts under the hood. **Always use Charts API v2** — the legacy v1 is superseded.

All v2 chart blocks live in the **`OutSystemsCharts/Charts`** flow. Block names are bare (`DonutChart`, not `DonutChart_v2`).

## Available chart blocks

| Block | Use when |
|---|---|
| `ColumnChart` | Compare values across categories (vertical bars) |
| `BarChart` | Compare values across categories (horizontal bars) |
| `LineChart` | Trend over time |
| `AreaChart` | Cumulative trend / volume over time |
| `PieChart` | Part-to-whole |
| `DonutChart` | Part-to-whole with a hole in the middle |
| `ScatterChart` | Correlation between two variables |
| `PackedBubbleChart` | Hierarchical categorical data |
| `Treemap` | Hierarchical categorical data (rectangles) |

Quick guide:
- **Few categories, one metric per category** → Column / Bar
- **Time series** → Line / Area
- **Composition adding to 100%** → Pie / Donut
- **Two-variable correlation** → Scatter

## Addons (drop into the chart's `AddOns_Placeholder`)

| Addon block | Configures |
|---|---|
| `ChartLegend` | Legend layout + position (top / bottom / left / right; vertical / horizontal) |
| `ChartSeriesStyling` | Per-series colors, line widths, markers |

## Spec conventions

- Charts bind to a **DataPointList** — a list of records with `Label`, `Value`, and optional `SeriesName`, `Color`, `Tooltip`. Spec names the source aggregate; Mentor handles the data binding.
- Charts have **no Title input** — wrap in `CardSectioned` and use its `Title` placeholder for the heading.
- Charts have **no built-in empty state** — spec a `BlankSlate` fallback via `IfWidget` for no-data scenarios.
- For Highcharts options not exposed as inputs (custom tooltip formatters, plot lines, animation tweaks), name the **`SetHighcharts*Configs`** Client Action in the spec — Mentor wires the call from the chart's `Initialized` event.

## Anti-patterns

- ❌ Spec a chart as custom HTML/CSS/JS instead of using a chart block.
- ❌ One chart per data point — twelve monthly values = one chart with 12 points, not 12 single-point charts.
- ❌ Hardcoded chart colors — use the `ChartSeriesStyling` addon.
- ❌ Reference `AdvancedFormat` — removed in v2.
- ❌ Block names with `_v2` suffix — block names are bare (`DonutChart`).
- ❌ Color alone to communicate categories — pair with shape/pattern for color-blind users.

## References

- [OutSystems Charts showcase](https://charts.outsystems.com) — interactive examples of every chart type.
- [Charts API v2 reference](https://success.outsystems.com/documentation/11/reference/outsystems_apis/charts_api_v2/) — full per-chart input list.
