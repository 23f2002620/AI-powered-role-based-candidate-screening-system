export default function Loader({ label = "Loading..." }) {
  return (
    <div className="loading-panel">
      <div className="spinner" />
      <div>{label}</div>
    </div>
  );
}
