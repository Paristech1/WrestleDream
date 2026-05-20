/**
 * Vite dev proxy: forwards /api/* to WrestleDream FastAPI backend (port 8000).
 */

const BACKEND = process.env.WRESTLEDREAM_API || 'http://127.0.0.1:8000';

export default function devApiPlugin() {
  return {
    name: 'wrestledream-api-proxy',
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        if (!req.url?.startsWith('/api/')) return next();
        const target = `${BACKEND}${req.url}`;
        try {
          const response = await fetch(target, { headers: { Accept: 'application/json' } });
          const body = await response.text();
          res.statusCode = response.status;
          res.setHeader('Content-Type', 'application/json');
          res.setHeader('Access-Control-Allow-Origin', '*');
          res.end(body);
        } catch (err) {
          res.statusCode = 502;
          res.setHeader('Content-Type', 'application/json');
          res.end(
            JSON.stringify({
              message: `Backend unreachable at ${BACKEND}. Start: cd backend && uvicorn main:app --reload --port 8000`,
              pairs: [],
            }),
          );
        }
      });
    },
  };
}
