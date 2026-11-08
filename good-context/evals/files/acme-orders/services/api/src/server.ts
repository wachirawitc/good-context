import Fastify from 'fastify';
import { ordersRoutes } from './routes/orders';
import { logger } from './lib/logger';

const app = Fastify({ loggerInstance: logger });
app.register(ordersRoutes);

app.listen({ port: Number(process.env.PORT ?? 3000) });
