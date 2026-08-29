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
        JWT_SECRET: 'change-me-in-production'
      },
      out_file: '/var/log/pulse-auth-out.log',
      error_file: '/var/log/pulse-auth-err.log',
    }
  ]
};
