'use client';

import { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import axios from 'axios';

const API_BASE = 'http://localhost:8000';

interface StockChartProps {
  symbol: string;
  height?: number;
}

interface HistoryPoint {
  date: string;
  close: number;
  sma_20: number | null;
  sma_50: number | null;
}

export default function StockChart({ symbol, height = 300 }: StockChartProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<HistoryPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await axios.get(`${API_BASE}/api/stock/${symbol}?period=6mo`);
        setData(response.data.history);
      } catch (error) {
        console.error('Error fetching chart data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [symbol]);

  useEffect(() => {
    if (!svgRef.current || !containerRef.current || data.length === 0) return;

    const container = containerRef.current;
    const width = container.clientWidth;
    const margin = { top: 20, right: 40, bottom: 30, left: 50 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    // Clear previous chart
    d3.select(svgRef.current).selectAll('*').remove();

    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height);

    const g = svg.append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Parse dates
    const parseDate = d3.timeParse('%Y-%m-%dT%H:%M:%S');
    const parsedData = data.map(d => ({
      ...d,
      date: parseDate(d.date.split('.')[0]) || new Date(d.date),
    }));

    // Scales
    const xScale = d3.scaleTime()
      .domain(d3.extent(parsedData, d => d.date) as [Date, Date])
      .range([0, innerWidth]);

    const yScale = d3.scaleLinear()
      .domain([
        d3.min(parsedData, d => d.close) as number * 0.98,
        d3.max(parsedData, d => d.close) as number * 1.02
      ])
      .range([innerHeight, 0]);

    // Grid lines
    g.append('g')
      .attr('class', 'grid')
      .attr('transform', `translate(0,${innerHeight})`)
      .call(d3.axisBottom(xScale)
        .tickSize(-innerHeight)
        .tickFormat(() => '')
      );

    g.append('g')
      .attr('class', 'grid')
      .call(d3.axisLeft(yScale)
        .tickSize(-innerWidth)
        .tickFormat(() => '')
      );

    // Area gradient
    const gradient = svg.append('defs')
      .append('linearGradient')
      .attr('id', 'areaGradient')
      .attr('x1', '0%')
      .attr('y1', '0%')
      .attr('x2', '0%')
      .attr('y2', '100%');

    gradient.append('stop')
      .attr('offset', '0%')
      .attr('stop-color', '#3b82f6')
      .attr('stop-opacity', 0.3);

    gradient.append('stop')
      .attr('offset', '100%')
      .attr('stop-color', '#3b82f6')
      .attr('stop-opacity', 0);

    // Area
    const area = d3.area<typeof parsedData[0]>()
      .x(d => xScale(d.date))
      .y0(innerHeight)
      .y1(d => yScale(d.close))
      .curve(d3.curveMonotoneX);

    g.append('path')
      .datum(parsedData)
      .attr('fill', 'url(#areaGradient)')
      .attr('d', area);

    // Line
    const line = d3.line<typeof parsedData[0]>()
      .x(d => xScale(d.date))
      .y(d => yScale(d.close))
      .curve(d3.curveMonotoneX);

    g.append('path')
      .datum(parsedData)
      .attr('fill', 'none')
      .attr('stroke', '#3b82f6')
      .attr('stroke-width', 2)
      .attr('d', line);

    // SMA 20
    const sma20Line = d3.line<typeof parsedData[0]>()
      .defined(d => d.sma_20 !== null)
      .x(d => xScale(d.date))
      .y(d => yScale(d.sma_20 as number))
      .curve(d3.curveMonotoneX);

    g.append('path')
      .datum(parsedData)
      .attr('fill', 'none')
      .attr('stroke', '#f59e0b')
      .attr('stroke-width', 1.5)
      .attr('stroke-dasharray', '4,2')
      .attr('d', sma20Line);

    // SMA 50
    const sma50Line = d3.line<typeof parsedData[0]>()
      .defined(d => d.sma_50 !== null)
      .x(d => xScale(d.date))
      .y(d => yScale(d.sma_50 as number))
      .curve(d3.curveMonotoneX);

    g.append('path')
      .datum(parsedData)
      .attr('fill', 'none')
      .attr('stroke', '#ef4444')
      .attr('stroke-width', 1.5)
      .attr('stroke-dasharray', '4,2')
      .attr('d', sma50Line);

    // Axes
    g.append('g')
      .attr('transform', `translate(0,${innerHeight})`)
      .call(d3.axisBottom(xScale).ticks(6))
      .selectAll('text')
      .attr('fill', '#888')
      .style('font-size', '11px');

    g.append('g')
      .call(d3.axisLeft(yScale).ticks(5).tickFormat(d => `$${d}`))
      .selectAll('text')
      .attr('fill', '#888')
      .style('font-size', '11px');

    // Tooltip
    const tooltip = d3.select(container)
      .append('div')
      .attr('class', 'chart-tooltip')
      .style('opacity', 0);

    const bisect = d3.bisector<typeof parsedData[0], Date>(d => d.date).left;

    g.append('rect')
      .attr('width', innerWidth)
      .attr('height', innerHeight)
      .attr('fill', 'transparent')
      .on('mousemove', (event) => {
        const [mouseX] = d3.pointer(event);
        const x0 = xScale.invert(mouseX);
        const i = bisect(parsedData, x0, 1);
        const d0 = parsedData[i - 1];
        const d1 = parsedData[i];
        const d = d1 && (x0.getTime() - d0.date.getTime() > d1.date.getTime() - x0.getTime()) ? d1 : d0;

        if (d) {
          tooltip
            .style('opacity', 1)
            .html(`
              <div class="font-medium text-white">${d.date.toLocaleDateString()}</div>
              <div class="text-primary-400">$${d.close.toFixed(2)}</div>
              ${d.sma_20 ? `<div class="text-yellow-400 text-xs">SMA20: $${d.sma_20.toFixed(2)}</div>` : ''}
            `)
            .style('left', `${event.offsetX + 10}px`)
            .style('top', `${event.offsetY - 30}px`);
        }
      })
      .on('mouseout', () => {
        tooltip.style('opacity', 0);
      });

    // Legend
    const legend = svg.append('g')
      .attr('transform', `translate(${margin.left + 10}, ${margin.top})`);

    const legendItems = [
      { color: '#3b82f6', label: 'Price' },
      { color: '#f59e0b', label: 'SMA 20' },
      { color: '#ef4444', label: 'SMA 50' },
    ];

    legendItems.forEach((item, i) => {
      const lg = legend.append('g')
        .attr('transform', `translate(${i * 80}, 0)`);

      lg.append('line')
        .attr('x1', 0)
        .attr('x2', 15)
        .attr('y1', 0)
        .attr('y2', 0)
        .attr('stroke', item.color)
        .attr('stroke-width', 2);

      lg.append('text')
        .attr('x', 20)
        .attr('y', 4)
        .attr('fill', '#888')
        .style('font-size', '11px')
        .text(item.label);
    });

    return () => {
      tooltip.remove();
    };
  }, [data, height]);

  if (loading) {
    return (
      <div className="h-[300px] loading-shimmer rounded-lg" />
    );
  }

  return (
    <div ref={containerRef} className="w-full relative">
      <svg ref={svgRef} />
    </div>
  );
}
