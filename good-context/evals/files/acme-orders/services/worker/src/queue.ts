import { Queue } from 'bullmq';
import IORedis from 'ioredis';

export const connection = new IORedis(process.env.REDIS_URL ?? 'redis://localhost:6379', {
  maxRetriesPerRequest: null,
});

// On-call alerting thresholds are tuned to these values.
export const defaultJobOptions = { attempts: 5, backoff: { type: 'exponential', delay: 2000 } };

export const ordersQueue = new Queue('orders', { connection, defaultJobOptions });
