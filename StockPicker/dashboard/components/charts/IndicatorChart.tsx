'use client';

import { useEffect, useRef } from 'react';
import * as d3 from 'd3';

interface DataPoint {
  date: string;
  value: number | null;
}

interface IndicatorChartProps {
  data: DataPoint[];
  label: string;
  height?: number;
  thresholds?: number[];
}

export default function IndicatorChart({ data, label, height = 150, thresholds = [] }: IndicatorChartProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!svgRef.current || !containerRef.current || data.length === 0) return;

    const container = containerRef.current;
    const width = container.clientWidth;
    const margin = { top: 25, right: 40, bottom: 20, left: 40 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    d3.select(svgRef.current).selectAll('*').remove();

    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height);

    const g = svg.append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Filter valid data
    const validData = data.filter(d => d.value !== null).slice(-90);
    
    const parseDate = d3.timeParse('%Y-%m-%dT%H:%M:%S');
    const parsedData = validData.map(d => ({
      ...d,
      date: parseDate(d.date.split('.')[0]) || new Date(d.date),
      value: d.value as number,
    }));

    // Scales
    const xScale = d3.scaleTime()
      .domain(d3.extent(parsedData, d => d.date) as [Date, Date])
      .range([0, innerWidth]);

    const yExtent = d3.extent(parsedData, d => d.value) as [number, number];
    const yPadding = (yExtent[1] - yExtent[0]) * 0.1;
    
    const yScale = d3.scaleLinear()
      .domain([yExtent[0] - yPadding, yExtent[1] + yPadding])
      .range([innerHeight, 0]);

    // Threshold lines
    thresholds.forEach(threshold => {
      g.append('line')
        .attr('x1', 0)
        .attr('x2', innerWidth)
        .attr('y1', yScale(threshold))
        .attr('y2', yScale(threshold))
        .attr('stroke', threshold < 50 ? '#10b981' : '#ef4444')
        .attr('stroke-width', 1)
        .attr('stroke-dasharray', '4,4')
        .attr('opacity', 0.5);

      g.append('text')
        .attr('x', innerWidth + 5)
        .attr('y', yScale(threshold) + 4)
        .attr('fill', threshold < 50 ? '#10b981' : '#ef4444')
        .style('font-size', '10px')
        .text(threshold.toString());
    });

    // Grid
    g.append('g')
      .attr('class', 'grid')
      .call(d3.axisLeft(yScale)
        .tickSize(-innerWidth)
        .tickFormat(() => '')
        .ticks(4)
      );

    // Line
    const line = d3.line<typeof parsedData[0]>()
      .x(d => xScale(d.date))
      .y(d => yScale(d.value))
      .curve(d3.curveMonotoneX);

    g.append('path')
      .datum(parsedData)
      .attr('fill', 'none')
      .attr('stroke', '#3b82f6')
      .attr('stroke-width', 1.5)
      .attr('d', line);

    // Label
    svg.append('text')
      .attr('x', margin.left)
      .attr('y', 16)
      .attr('fill', '#888')
      .style('font-size', '12px')
      .style('font-weight', '500')
      .text(label);

    // Current value
    const lastValue = parsedData[parsedData.length - 1]?.value;
    if (lastValue !== undefined) {
      svg.append('text')
        .attr('x', width - margin.right)
        .attr('y', 16)
        .attr('text-anchor', 'end')
        .attr('fill', '#fff')
        .style('font-size', '12px')
        .style('font-weight', '500')
        .text(lastValue.toFixed(2));
    }

    // Y Axis
    g.append('g')
      .call(d3.axisLeft(yScale).ticks(4))
      .selectAll('text')
      .attr('fill', '#888')
      .style('font-size', '10px');

  }, [data, height, label, thresholds]);

  return (
    <div ref={containerRef} className="w-full bg-[#0f0f1a] rounded-lg p-2">
      <svg ref={svgRef} />
    </div>
  );
}
