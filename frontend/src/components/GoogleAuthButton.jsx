import React from "react";

/**
 * "Continue with Google" — Emergent-managed OAuth.
 *
 * REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
 */
export default function GoogleAuthButton({ label = "Continue with Google", testId = "google-auth-button" }) {
  const handleClick = () => {
    const redirectUrl = window.location.origin + "/dashboard";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };
  return (
    <button
      type="button"
      onClick={handleClick}
      data-testid={testId}
      className="w-full flex items-center justify-center gap-3 border border-white/15 bg-white/[0.02] hover:bg-white/[0.06] text-white rounded-full py-3 transition-colors duration-300"
    >
      <GoogleGlyph />
      <span className="text-sm">{label}</span>
    </button>
  );
}

function GoogleGlyph() {
  return (
    <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.4 29.3 35.5 24 35.5c-6.4 0-11.5-5.1-11.5-11.5S17.6 12.5 24 12.5c2.9 0 5.5 1.1 7.5 2.8l5.7-5.7C33.6 6 29.1 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.2-.1-2.3-.4-3.5z" />
      <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.6 15.7 18.9 12.5 24 12.5c2.9 0 5.5 1.1 7.5 2.8l5.7-5.7C33.6 6 29.1 4 24 4 16.3 4 9.6 8.4 6.3 14.7z" />
      <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2c-2 1.4-4.5 2.3-7.2 2.3-5.3 0-9.7-3.1-11.4-7.5l-6.5 5C9.5 39.6 16.2 44 24 44z" />
      <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.9 2.4-2.5 4.4-4.6 5.7l6.2 5.2C39 34.9 44 30 44 24c0-1.2-.1-2.3-.4-3.5z" />
    </svg>
  );
}
