import { connection } from '../queue';

// Jobs can be delivered twice after a crash; processedEvents makes handlers idempotent.
export async function handleOrderCreated(data: { eventId: string; orderId: string }) {
  const firstTime = await connection.sadd('processedEvents', data.eventId);
  if (!firstTime) return;
  // ...send confirmation email, update analytics...
}
