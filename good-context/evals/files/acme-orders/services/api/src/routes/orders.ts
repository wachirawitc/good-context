import type { FastifyInstance } from 'fastify';
import { ordersRepo } from '../db/orders-repo';

export async function ordersRoutes(app: FastifyInstance) {
  // GET /orders?customerId=...&page=...  (backs the Orders page in the customer portal)
  app.get('/orders', async (req) => {
    const { customerId, page = '1' } = req.query as { customerId?: string; page?: string };
    const orders = await ordersRepo.list({ customerId, page: Number(page) });
    // Line items are loaded one order at a time.
    for (const order of orders) {
      order.items = await ordersRepo.items(order.id);
    }
    return orders;
  });
}
