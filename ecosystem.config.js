module.exports = {
  apps: [
    {
      name: 'pulse-api',
      script: '/root/pulse/target/release/pulse',
      env: {
        REDIS_URL: 'redis://localhost:6379',
        BIND_ADDR: '0.0.0.0:7070',
        RUST_LOG: 'info'
      },
      out_file: '/var/log/pulse-out.log',
      error_file: '/var/log/pulse-err.log',
    },
    {
      name: 'pulse-auth',
      script: '/root/pulse/.venv/bin/uvicorn',
      args: 'auth_service:app --host 127.0.0.1 --port 7072 --workers 1',
      cwd: '/root/pulse',
      env: {
        DB_PATH: '/root/pulse/pulse.db',
        PULSE_API_URL: 'http://localhost:7070',
        JWT_SECRET: 'change-me-in-production',
        // Google OAuth — paste ID + secret from Google Cloud Console to go live.
        // While these are empty, the Google button uses a demo-account fallback.
        // If the public domain changes, update GOOGLE_REDIRECT_URI here AND in the
        // Google Cloud Console "Authorized redirect URIs" list (must match exactly).
        GOOGLE_CLIENT_ID: '',
        GOOGLE_CLIENT_SECRET: '',
        GOOGLE_REDIRECT_URI: 'https://pulse.94.72.105.176.sslip.io/auth/google/callback'
      },
      out_file: '/var/log/pulse-auth-out.log',
      error_file: '/var/log/pulse-auth-err.log',
    }
  ]
};
