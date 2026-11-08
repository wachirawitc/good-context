import { PrismaClient } from '@prisma/client';

// Only the repositories in this folder may use the Prisma client directly.
export const prisma = new PrismaClient();
