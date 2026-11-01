/** Four small diagrams for the Algorithms page. Decorative: each step is also explained in text. */
const ink = 'var(--color-ink)';
const soft = 'var(--color-line)';
const Node = ({ x, y, label, fill = 'var(--color-surface)', stroke = ink }: { x: number; y: number; label: string; fill?: string; stroke?: string }) => (
  <g><circle cx={x} cy={y} r="15" fill={fill} stroke={stroke} strokeWidth="1.5" /><text x={x} y={y} dy="0.35em" textAnchor="middle" fontSize="12" fontWeight="600" fill={ink}>{label}</text></g>
);
const Arrow = ({ x1, y1, x2, y2, color = ink }: { x1: number; y1: number; x2: number; y2: number; color?: string }) => {
  const a = Math.atan2(y2 - y1, x2 - x1);
  const ex = x2 - Math.cos(a) * 17, ey = y2 - Math.sin(a) * 17, sx = x1 + Math.cos(a) * 17, sy = y1 + Math.sin(a) * 17;
  const h = [[ex, ey], [ex - Math.cos(a - 0.45) * 8, ey - Math.sin(a - 0.45) * 8], [ex - Math.cos(a + 0.45) * 8, ey - Math.sin(a + 0.45) * 8]];
  return <g><line x1={sx} y1={sy} x2={ex} y2={ey} stroke={color} strokeWidth="1.6" strokeLinecap="round" /><path d={`M${h[0]} L${h[1]} L${h[2]}z`} fill={color} /></g>;
};
const Frame = ({ children }: { children: React.ReactNode }) => <svg viewBox="0 0 200 110" className="w-full" aria-hidden>{children}</svg>;

export const GraphDiagram = () => (<Frame><Node x={30} y={55} label="A" /><Node x={100} y={25} label="B" /><Node x={100} y={85} label="C" /><Node x={170} y={55} label="D" /><Arrow x1={30} y1={55} x2={100} y2={25} /><Arrow x1={30} y1={55} x2={100} y2={85} /><Arrow x1={100} y1={25} x2={170} y2={55} /><Arrow x1={100} y1={85} x2={170} y2={55} /></Frame>);
export const CycleDiagram = () => (<Frame><Node x={45} y={80} label="A" fill="var(--color-error-bg)" stroke="var(--color-error)" /><Node x={100} y={25} label="B" fill="var(--color-error-bg)" stroke="var(--color-error)" /><Node x={155} y={80} label="C" fill="var(--color-error-bg)" stroke="var(--color-error)" /><Arrow x1={45} y1={80} x2={100} y2={25} color="var(--color-error)" /><Arrow x1={100} y1={25} x2={155} y2={80} color="var(--color-error)" /><Arrow x1={155} y1={80} x2={45} y2={80} color="var(--color-error)" /></Frame>);
export const SortDiagram = () => (<Frame>{[1, 2, 3, 4].map((n, i) => <Node key={n} x={28 + i * 48} y={55} label={String(n)} fill="var(--color-info-bg)" stroke="var(--color-accent)" />)}{[0, 1, 2].map((i) => <Arrow key={i} x1={28 + i * 48} y1={55} x2={28 + (i + 1) * 48} y2={55} />)}</Frame>);
export const SemesterDiagram = () => {
  const block = (x: number, y: number, w: number) => <rect x={x} y={y} width={w} height="22" rx="6" fill="var(--color-surface)" stroke={ink} strokeWidth="1.5" />;
  return (<Frame>{block(8, 16, 50)}{block(8, 46, 50)}{block(76, 31, 50)}{block(144, 16, 48)}{block(144, 46, 48)}<path d="M8 90h50M76 90h50M144 90h48" stroke={soft} strokeWidth="3" strokeLinecap="round" /><path d="M62 31l10 8M62 57l10-10M130 40l10-12M130 44l10 12" stroke={ink} strokeWidth="1.4" strokeLinecap="round" fill="none" /></Frame>);
};
