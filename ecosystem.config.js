module.exports = {
  apps: [{
    name: 'pulse-api',
    script: '/root/pulse/target/release/pulse',
    env: {
      REDIS_URL: 'redis://127.0.0.1:6379',
      BIND_ADDR: '0.0.0.0:7070',
      RUST_LOG: 'pulse=info',
    },
    error_file: '/var/log/pulse-err.log',
    out_file: '/var/log/pulse-out.log',
    restart_delay: 2000,
    max_restarts: 10,
  }]
};

// MCP server (stdio — spawned per client, no persistent process needed)
// Kept here for reference. Claude Desktop spawns it directly.
