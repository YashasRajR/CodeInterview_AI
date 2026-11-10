/** Brand mark: a marker-drawn circle around a tick, like an interviewer grading on a whiteboard. */
export default function Logo({ size = 30 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
      <rect x="2" y="2" width="60" height="60" rx="12" fill="#1b2a4a" />
      <path d="M36 10 C52 9 58 22 55 35 C51 51 22 56 12 43 C4 32 10 15 26 11 C31 10 36 10 41 12"
        fill="none" stroke="#ffffff" strokeWidth="4.5" strokeLinecap="round" />
      <path d="M21 33 L29 41 L44 23" fill="none" stroke="#5b8cf0" strokeWidth="6"
        strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
