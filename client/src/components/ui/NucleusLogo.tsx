import { cn } from "@/lib/utils";

interface NucleusLogoProps {
  className?: string;
  variant?: "full" | "icon";
  color?: string;
}

export function NucleusLogo({ className, variant = "full", color = "currentColor" }: NucleusLogoProps) {
  return (
    <div className={cn("flex items-center gap-3", className)}>
      {/* DNA Helix Icon - Stylized SVG */}
      <svg
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-8 h-8 md:w-10 md:h-10 text-nucleus-gold"
      >
        <path
          d="M30 20C30 20 50 40 70 20M30 80C30 80 50 60 70 80"
          stroke="url(#gold-gradient)"
          strokeWidth="4"
          strokeLinecap="round"
          className="opacity-60"
        />
        <path
          d="M30 20C30 20 10 40 30 60C50 80 70 80 70 80"
          stroke="url(#gold-gradient)"
          strokeWidth="4"
          strokeLinecap="round"
        />
        <path
          d="M70 20C70 20 90 40 70 60C50 80 30 80 30 80"
          stroke="url(#cyan-gradient)"
          strokeWidth="4"
          strokeLinecap="round"
          className="opacity-80"
        />
        <defs>
          <linearGradient id="gold-gradient" x1="0" y1="0" x2="100" y2="100" gradientUnits="userSpaceOnUse">
            <stop stopColor="#D4AF37" />
            <stop offset="1" stopColor="#F2D06B" />
          </linearGradient>
          <linearGradient id="cyan-gradient" x1="100" y1="0" x2="0" y2="100" gradientUnits="userSpaceOnUse">
            <stop stopColor="#00D9FF" />
            <stop offset="1" stopColor="#0080FF" />
          </linearGradient>
        </defs>
      </svg>

      {/* Typography - Only shown in 'full' variant */}
      {variant === "full" && (
        <div className="flex flex-col justify-center">
          <span className="font-serif text-xl md:text-2xl font-bold tracking-[0.15em] leading-none text-white">
            NUCLEUS
          </span>
          <span className="text-[8px] md:text-[10px] tracking-[0.4em] text-nucleus-cyan uppercase leading-none mt-1 opacity-80">
            Symbiont
          </span>
        </div>
      )}
    </div>
  );
}
