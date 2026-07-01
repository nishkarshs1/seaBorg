import { motion, type HTMLMotionProps } from "framer-motion";
import { forwardRef } from "react";
import { cn } from "@/lib/utils";

type Props = HTMLMotionProps<"div"> & { hover?: boolean };

export const GlassCard = forwardRef<HTMLDivElement, Props>(
  ({ className, hover = true, children, ...props }, ref) => (
    <motion.div
      ref={ref}
      whileHover={hover ? { scale: 1.015, y: -2 } : undefined}
      transition={{ type: "spring", stiffness: 280, damping: 22 }}
      className={cn("glass px-6 py-5", className)}
      {...props}
    >
      {children}
    </motion.div>
  ),
);
GlassCard.displayName = "GlassCard";
