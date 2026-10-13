/** jobFinder's mark: three steps up, and the mark just out of reach. Drawn in the text colour, so it
 *  is ink in light mode and follows dark mode by itself. */
export function Logo() {
  return (
    <svg className="logo" viewBox="0 0 32 32" width="32" height="32" aria-hidden="true" focusable="false">
      <path
        d="M3 28.5H11V20.5H19V12.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="25.5" cy="6.5" r="4" fill="currentColor" />
    </svg>
  );
}
