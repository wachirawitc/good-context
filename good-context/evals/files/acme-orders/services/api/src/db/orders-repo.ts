import { prisma } from './client';

const PAGE_SIZE = 50;

export const ordersRepo = {
  list: ({ customerId, page }: { customerId?: string; page: number }) =>
    prisma.order.findMany({
      where: customerId ? { customerId } : undefined,
      skip: (page - 1) * PAGE_SIZE,
      take: PAGE_SIZE,
      orderBy: { createdAt: 'desc' },
    }) as Promise<any[]>,
  items: (orderId: string) => prisma.lineItem.findMany({ where: { orderId } }),
};
