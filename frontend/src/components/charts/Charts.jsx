import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { EmptyState } from '../common/States.jsx';

const COLORS = ['#4ade80', '#2dd4bf', '#a3e635', '#34d399', '#60a5fa', '#fbbf24', '#fb7185'];
export function ChartFrame({ data, children, height = 260, empty = 'No chart data is available.', label = 'Data chart' }) {
  if (!Array.isArray(data) || !data.length) return <EmptyState title="Nothing to chart yet">{empty}</EmptyState>;
  return <div className="chart-frame" role="img" aria-label={label} style={{ height }}><ResponsiveContainer width="100%" height="100%">{children}</ResponsiveContainer></div>;
}
export function TrendChart({ data, xKey = 'month', yKey = 'value', empty }) {
  return <ChartFrame data={data} empty={empty} label={`Trend chart: ${yKey} by ${xKey}`}><LineChart data={data} margin={{ top: 10, right: 12, bottom: 0, left: -16 }}><CartesianGrid stroke="#253630" strokeDasharray="4 6" vertical={false} /><XAxis dataKey={xKey} tick={{ fill: '#82918a', fontSize: 11 }} axisLine={false} tickLine={false} /><YAxis tick={{ fill: '#82918a', fontSize: 11 }} axisLine={false} tickLine={false} /><Tooltip contentStyle={{ background: '#10201b', border: '1px solid #2b3e37', borderRadius: 12 }} /><Line dataKey={yKey} stroke="#4ade80" strokeWidth={2.5} dot={false} activeDot={{ r: 5 }} /></LineChart></ChartFrame>;
}
export function BarsChart({ data, xKey = 'name', yKey = 'value', empty, color = '#4ade80' }) {
  return <ChartFrame data={data} empty={empty} label={`Bar chart: ${yKey} by ${xKey}`}><BarChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -16 }}><CartesianGrid stroke="#253630" strokeDasharray="4 6" vertical={false} /><XAxis dataKey={xKey} tick={{ fill: '#82918a', fontSize: 11 }} axisLine={false} tickLine={false} /><YAxis tick={{ fill: '#82918a', fontSize: 11 }} axisLine={false} tickLine={false} /><Tooltip contentStyle={{ background: '#10201b', border: '1px solid #2b3e37', borderRadius: 12 }} /><Bar dataKey={yKey} fill={color} radius={[5, 5, 0, 0]} /></BarChart></ChartFrame>;
}
export function DonutChart({ data, nameKey = 'name', valueKey = 'value', empty }) {
  return <ChartFrame data={data} empty={empty} label={`Distribution chart: ${valueKey} grouped by ${nameKey}`}><PieChart><Pie data={data} dataKey={valueKey} nameKey={nameKey} innerRadius="58%" outerRadius="82%" paddingAngle={3} stroke="none">{data.map((_, index) => <Cell key={index} fill={COLORS[index % COLORS.length]} />)}</Pie><Tooltip contentStyle={{ background: '#10201b', border: '1px solid #2b3e37', borderRadius: 12 }} /></PieChart></ChartFrame>;
}
