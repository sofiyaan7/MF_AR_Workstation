/**
 * Chart primitives for the analytics pages.
 *
 * All series come from the API. Colours are read from the same CSS custom
 * properties as the rest of the design system, so charts follow the theme
 * (including dark mode) without a second palette to maintain.
 */
import * as React from "react";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";

import { EmptyState } from "@/components/ui/states";
import { chartDateLabel, formatNumber } from "@/lib/format";

const CHART_COLOURS = [
  "hsl(var(--chart-1))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-3))",
  "hsl(var(--chart-4))",
  "hsl(var(--chart-5))",
];

const axisProps = {
  stroke: "hsl(var(--muted-foreground))",
  fontSize: 11,
  tickLine: false,
  axisLine: false,
} as const;

interface TooltipPayloadItem {
  value?: number | string;
  name?: string;
  payload?: Record<string, unknown>;
}

function ChartTooltip({
  active, payload, label, valueLabel,
}: {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: string | number;
  valueLabel: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-md border border-border bg-popover px-3 py-2 shadow-popover">
      <p className="text-xs font-medium text-foreground">{label}</p>
      <p className="mt-0.5 text-xs text-muted-foreground">
        <span className="font-semibold tabular-nums text-foreground">
          {formatNumber(Number(payload[0].value ?? 0))}
        </span>{" "}
        {valueLabel}
      </p>
    </div>
  );
}

interface TrendChartProps {
  data: { date: string; count: number }[];
  valueLabel: string;
  colourIndex?: number;
  height?: number;
}

/** Daily trend line — used for active users, sign-ins and project opens. */
export function TrendChart({ data, valueLabel, colourIndex = 0, height = 240 }: TrendChartProps) {
  const gradientId = React.useId();
  const colour = CHART_COLOURS[colourIndex % CHART_COLOURS.length];
  const hasData = data.some((point) => point.count > 0);

  if (!hasData) {
    return (
      <EmptyState
        title="No data for this period"
        description={`Nothing has been recorded for ${valueLabel} yet.`}
        className="py-10"
      />
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={colour} stopOpacity={0.28} />
            <stop offset="100%" stopColor={colour} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
        <XAxis dataKey="date" tickFormatter={chartDateLabel} minTickGap={28} {...axisProps} />
        <YAxis allowDecimals={false} width={44} {...axisProps} />
        <Tooltip
          content={<ChartTooltip valueLabel={valueLabel} />}
          labelFormatter={(value) => chartDateLabel(String(value))}
          cursor={{ stroke: "hsl(var(--border))" }}
        />
        <Area
          type="monotone"
          dataKey="count"
          stroke={colour}
          strokeWidth={2}
          fill={`url(#${gradientId})`}
          dot={false}
          activeDot={{ r: 4, strokeWidth: 0 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

interface UsageBarChartProps {
  data: { label: string; value: number }[];
  valueLabel: string;
  height?: number;
}

/** Horizontal bars — the natural form for ranked project usage. */
export function UsageBarChart({ data, valueLabel, height }: UsageBarChartProps) {
  if (data.length === 0) {
    return (
      <EmptyState
        title="No usage recorded yet"
        description="Project opens will appear here as your team starts using the portal."
        className="py-10"
      />
    );
  }

  const computedHeight = height ?? Math.max(180, data.length * 38 + 24);

  return (
    <ResponsiveContainer width="100%" height={computedHeight}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
        <XAxis type="number" allowDecimals={false} {...axisProps} />
        <YAxis
          type="category"
          dataKey="label"
          width={150}
          tick={{ fontSize: 11, fill: "hsl(var(--foreground))" }}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip
          content={<ChartTooltip valueLabel={valueLabel} />}
          cursor={{ fill: "hsl(var(--muted))" }}
        />
        <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={18}>
          {data.map((entry, index) => (
            <Cell key={entry.label} fill={CHART_COLOURS[index % CHART_COLOURS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Compact inline bar list — used where a full chart would be too heavy. */
export function BarList({
  items,
  valueLabel = "opens",
}: {
  items: { label: string; value: number; hint?: string }[];
  valueLabel?: string;
}) {
  if (items.length === 0) {
    return <p className="py-6 text-center text-sm text-muted-foreground">No data yet.</p>;
  }
  const max = Math.max(...items.map((item) => item.value), 1);

  return (
    <ul className="space-y-2.5">
      {items.map((item, index) => (
        <li key={`${item.label}-${index}`}>
          <div className="mb-1 flex items-baseline justify-between gap-3">
            <span className="truncate text-sm text-foreground">{item.label}</span>
            <span className="shrink-0 text-xs tabular-nums text-muted-foreground">
              {formatNumber(item.value)} {valueLabel}
            </span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full transition-[width] duration-500"
              style={{
                width: `${Math.max(2, (item.value / max) * 100)}%`,
                backgroundColor: CHART_COLOURS[index % CHART_COLOURS.length],
              }}
            />
          </div>
          {item.hint && <p className="mt-0.5 text-2xs text-muted-foreground">{item.hint}</p>}
        </li>
      ))}
    </ul>
  );
}
