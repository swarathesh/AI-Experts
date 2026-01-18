'use client';

import { useEffect, useRef } from 'react';
import * as d3 from 'd3';

interface DataPoint {
  date: string;
  open: number;
  close: number;
  volume: number;
}

interface VolumeChartProps {
  data: DataPoint[];
  height?: number;
}

export default function VolumeChart({ data, height = 100 }: VolumeChartProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!svgRef.current || !containerRef.current || data.length === 0) return;

    const container = containerRef.current;
    const width = container.clientWidth;
    const margin = { top: 10, right: 60, bottom: 20, left: 60 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    d3.select(svgRef.current).selectAll('*').remove();

    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height);

    const g = svg.append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Limit to last 90 days
    const recentData = data.slice(-90);

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
      .domain([0, d3.max(parsedData, d => d.volume) as number])
      .range([innerHeight, 0]);

    // Bars
    g.selectAll('.volume-bar')
      .data(parsedData)
      .enter()
      .append('rect')
      .attr('class', d => d.close >= d.open ? 'volume-up' : 'volume-down')
      .attr('x', d => xScale(d.date.toISOString()) as number)
      .attr('y', d => yScale(d.volume))
      .attr('width', xScale.bandwidth())
      .attr('height', d => innerHeight - yScale(d.volume))
      .attr('rx', 1);

    // Label
    svg.append('text')
      .attr('x', margin.left)
      .attr('y', height - 5)
      .attr('fill', '#666')
      .style('font-size', '10px')
      .text('Volume');

    // Y Axis
    g.append('g')
      .attr('transform', `translate(${innerWidth}, 0)`)
      .call(d3.axisRight(yScale)
        .ticks(3)
        .tickFormat(d => {
          const num = d as number;
          if (num >= 1e9) return `${(num / 1e9).toFixed(1)}B`;
          if (num >= 1e6) return `${(num / 1e6).toFixed(1)}M`;
          if (num >= 1e3) return `${(num / 1e3).toFixed(0)}K`;
          return num.toString();
        })
      )
      .selectAll('text')
      .attr('fill', '#666')
      .style('font-size', '10px');

  }, [data, height]);

  return (
    <div ref={containerRef} className="w-full">
      <svg ref={svgRef} />
    </div>
  );
}
