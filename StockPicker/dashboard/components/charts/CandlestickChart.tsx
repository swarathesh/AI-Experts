'use client';

import { useEffect, useRef } from 'react';
import * as d3 from 'd3';

interface DataPoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface CandlestickChartProps {
  data: DataPoint[];
  height?: number;
}

export default function CandlestickChart({ data, height = 400 }: CandlestickChartProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!svgRef.current || !containerRef.current || data.length === 0) return;

    const container = containerRef.current;
    const width = container.clientWidth;
    const margin = { top: 20, right: 60, bottom: 30, left: 60 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    // Clear previous
    d3.select(svgRef.current).selectAll('*').remove();

    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height);

    const g = svg.append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Limit to last 90 days for readability
    const recentData = data.slice(-90);

    // Parse dates
    const parseDate = d3.timeParse('%Y-%m-%dT%H:%M:%S');
    const parsedData = recentData.map(d => ({
      ...d,
      date: parseDate(d.date.split('.')[0]) || new Date(d.date),
    }));

    // Scales
    const xScale = d3.scaleBand()
      .domain(parsedData.map(d => d.date.toISOString()))
      .range([0, innerWidth])
      .padding(0.3);

    const yScale = d3.scaleLinear()
      .domain([
        d3.min(parsedData, d => d.low) as number * 0.99,
        d3.max(parsedData, d => d.high) as number * 1.01
      ])
      .range([innerHeight, 0]);

    // Grid
    g.append('g')
      .attr('class', 'grid')
      .call(d3.axisLeft(yScale)
        .tickSize(-innerWidth)
        .tickFormat(() => '')
      );

    // Candlesticks
    const candles = g.selectAll('.candle')
      .data(parsedData)
      .enter()
      .append('g')
      .attr('class', 'candle');

    // Wicks
    candles.append('line')
      .attr('x1', d => (xScale(d.date.toISOString()) as number) + xScale.bandwidth() / 2)
      .attr('x2', d => (xScale(d.date.toISOString()) as number) + xScale.bandwidth() / 2)
      .attr('y1', d => yScale(d.high))
      .attr('y2', d => yScale(d.low))
      .attr('stroke', d => d.close >= d.open ? '#10b981' : '#ef4444')
      .attr('stroke-width', 1);

    // Bodies
    candles.append('rect')
      .attr('x', d => xScale(d.date.toISOString()) as number)
      .attr('y', d => yScale(Math.max(d.open, d.close)))
      .attr('width', xScale.bandwidth())
      .attr('height', d => Math.max(1, Math.abs(yScale(d.open) - yScale(d.close))))
      .attr('fill', d => d.close >= d.open ? '#10b981' : '#ef4444')
      .attr('rx', 1);

    // Y Axis
    g.append('g')
      .attr('transform', `translate(${innerWidth}, 0)`)
      .call(d3.axisRight(yScale).ticks(8).tickFormat(d => `$${d}`))
      .selectAll('text')
      .attr('fill', '#888')
      .style('font-size', '11px');

    // X Axis (show fewer ticks)
    const xAxis = d3.axisBottom(xScale)
      .tickValues(parsedData.filter((_, i) => i % Math.ceil(parsedData.length / 6) === 0).map(d => d.date.toISOString()))
      .tickFormat(d => {
        const date = new Date(d as string);
        return d3.timeFormat('%b %d')(date);
      });

    g.append('g')
      .attr('transform', `translate(0,${innerHeight})`)
      .call(xAxis)
      .selectAll('text')
      .attr('fill', '#888')
      .style('font-size', '11px');

    // Tooltip
    const tooltip = d3.select(container)
      .append('div')
      .attr('class', 'chart-tooltip')
      .style('opacity', 0);

    candles
      .on('mouseover', (event, d) => {
        tooltip
          .style('opacity', 1)
          .html(`
            <div class="font-medium text-white mb-1">${d.date.toLocaleDateString()}</div>
            <div class="grid grid-cols-2 gap-x-3 text-xs">
              <span class="text-gray-400">Open:</span><span class="text-white">$${d.open.toFixed(2)}</span>
              <span class="text-gray-400">High:</span><span class="text-green-400">$${d.high.toFixed(2)}</span>
              <span class="text-gray-400">Low:</span><span class="text-red-400">$${d.low.toFixed(2)}</span>
              <span class="text-gray-400">Close:</span><span class="${d.close >= d.open ? 'text-green-400' : 'text-red-400'}">$${d.close.toFixed(2)}</span>
            </div>
          `)
          .style('left', `${event.offsetX + 10}px`)
          .style('top', `${event.offsetY - 60}px`);
      })
      .on('mouseout', () => {
        tooltip.style('opacity', 0);
      });

    // Current price line
    const lastPrice = parsedData[parsedData.length - 1]?.close;
    if (lastPrice) {
      g.append('line')
        .attr('x1', 0)
        .attr('x2', innerWidth)
        .attr('y1', yScale(lastPrice))
        .attr('y2', yScale(lastPrice))
        .attr('stroke', '#3b82f6')
        .attr('stroke-width', 1)
        .attr('stroke-dasharray', '4,4');

      g.append('rect')
        .attr('x', innerWidth + 2)
        .attr('y', yScale(lastPrice) - 10)
        .attr('width', 55)
        .attr('height', 20)
        .attr('fill', '#3b82f6')
        .attr('rx', 3);

      g.append('text')
        .attr('x', innerWidth + 30)
        .attr('y', yScale(lastPrice) + 4)
        .attr('text-anchor', 'middle')
        .attr('fill', 'white')
        .style('font-size', '11px')
        .style('font-weight', '500')
        .text(`$${lastPrice.toFixed(2)}`);
    }

    return () => {
      tooltip.remove();
    };
  }, [data, height]);

  return (
    <div ref={containerRef} className="w-full relative">
      <svg ref={svgRef} />
    </div>
  );
}
