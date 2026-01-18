'use client';

import { useEffect, useRef } from 'react';
import * as d3 from 'd3';

interface AllocationChartProps {
  weights: Record<string, number>;
}

const COLORS = [
  '#3b82f6', // blue
  '#10b981', // green
  '#f59e0b', // yellow
  '#ef4444', // red
  '#8b5cf6', // purple
  '#ec4899', // pink
  '#06b6d4', // cyan
  '#84cc16', // lime
];

export default function AllocationChart({ weights }: AllocationChartProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!svgRef.current || !containerRef.current) return;

    const container = containerRef.current;
    const size = Math.min(container.clientWidth, 300);
    const radius = size / 2;
    const innerRadius = radius * 0.6;

    d3.select(svgRef.current).selectAll('*').remove();

    const svg = d3.select(svgRef.current)
      .attr('width', size)
      .attr('height', size);

    const g = svg.append('g')
      .attr('transform', `translate(${radius}, ${radius})`);

    // Prepare data
    const data = Object.entries(weights)
      .filter(([, v]) => v > 0)
      .map(([symbol, weight], i) => ({
        symbol,
        weight,
        color: COLORS[i % COLORS.length]
      }));

    // Pie generator
    const pie = d3.pie<typeof data[0]>()
      .value(d => d.weight)
      .sort(null);

    const arc = d3.arc<d3.PieArcDatum<typeof data[0]>>()
      .innerRadius(innerRadius)
      .outerRadius(radius - 5);

    const hoverArc = d3.arc<d3.PieArcDatum<typeof data[0]>>()
      .innerRadius(innerRadius)
      .outerRadius(radius);

    // Draw slices
    const slices = g.selectAll('.slice')
      .data(pie(data))
      .enter()
      .append('g')
      .attr('class', 'slice');

    slices.append('path')
      .attr('d', arc)
      .attr('fill', d => d.data.color)
      .attr('stroke', '#1a1a2e')
      .attr('stroke-width', 2)
      .style('cursor', 'pointer')
      .on('mouseover', function(event, d) {
        d3.select(this)
          .transition()
          .duration(200)
          .attr('d', hoverArc);
        
        // Show tooltip
        tooltip
          .style('opacity', 1)
          .html(`
            <div class="font-medium text-white">${d.data.symbol}</div>
            <div class="text-primary-400">${d.data.weight.toFixed(1)}%</div>
          `);
      })
      .on('mousemove', function(event) {
        tooltip
          .style('left', `${event.offsetX + 10}px`)
          .style('top', `${event.offsetY - 30}px`);
      })
      .on('mouseout', function() {
        d3.select(this)
          .transition()
          .duration(200)
          .attr('d', arc);
        
        tooltip.style('opacity', 0);
      });

    // Center text
    g.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '-0.5em')
      .attr('fill', '#888')
      .style('font-size', '12px')
      .text('Total');

    g.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '0.8em')
      .attr('fill', '#fff')
      .style('font-size', '18px')
      .style('font-weight', 'bold')
      .text('100%');

    // Tooltip
    const tooltip = d3.select(container)
      .append('div')
      .attr('class', 'chart-tooltip')
      .style('opacity', 0);

    // Legend
    const legend = svg.append('g')
      .attr('transform', `translate(${size + 20}, 20)`);

    data.forEach((d, i) => {
      const lg = legend.append('g')
        .attr('transform', `translate(0, ${i * 25})`);

      lg.append('rect')
        .attr('width', 14)
        .attr('height', 14)
        .attr('rx', 3)
        .attr('fill', d.color);

      lg.append('text')
        .attr('x', 20)
        .attr('y', 11)
        .attr('fill', '#fff')
        .style('font-size', '12px')
        .text(`${d.symbol} (${d.weight.toFixed(1)}%)`);
    });

    return () => {
      tooltip.remove();
    };
  }, [weights]);

  return (
    <div ref={containerRef} className="flex justify-center">
      <svg ref={svgRef} style={{ overflow: 'visible' }} />
    </div>
  );
}
