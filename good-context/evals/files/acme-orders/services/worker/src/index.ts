import { Worker } from 'bullmq';
import { connection } from './queue';
import { handleOrderCreated } from './handlers/order-created';

const handlers: Record<string, (data: any) => Promise<void>> = {
  'order.created': handleOrderCreated,
};

new Worker('orders', async (job) => handlers[job.name]?.(job.data), { connection });
