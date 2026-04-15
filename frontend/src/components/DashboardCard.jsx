import './DashboardCard.css';

export default function DashboardCard({ icon, label, value, sub, gradient, id }) {
  return (
    <div className="dashCard" id={id} style={{ '--card-gradient': gradient }}>
      <div className="dashCardInner">
        <div className="dashCardIcon">{icon}</div>
        <div className="dashCardContent">
          <div className="dashCardValue">{value ?? '—'}</div>
          <div className="dashCardLabel">{label}</div>
          {sub && <div className="dashCardSub">{sub}</div>}
        </div>
      </div>
    </div>
  );
}
