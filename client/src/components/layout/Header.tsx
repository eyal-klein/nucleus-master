import { useState, useEffect } from "react";
import { motion, useScroll, useTransform } from "framer-motion";
import { Link } from "wouter";
import { NucleusLogo } from "@/components/ui/NucleusLogo";

export function Header() {
  const [isScrolled, setIsScrolled] = useState(false);
  const { scrollY } = useScroll();
  
  useEffect(() => {
    return scrollY.onChange((latest) => {
      setIsScrolled(latest > 50);
    });
  }, [scrollY]);

  return (
    <motion.header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${
        isScrolled ? "py-4 bg-nucleus-navy/80 backdrop-blur-md border-b border-white/5" : "py-8 bg-transparent"
      }`}
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      transition={{ duration: 0.8, ease: "easeOut" }}
    >
      <div className="max-w-7xl mx-auto px-6 flex items-center justify-between">
        {/* Logo - SVG Component */}
        <Link href="/">
          <a className="relative group block">
            <NucleusLogo className="transition-all duration-500 opacity-90 group-hover:opacity-100 group-hover:drop-shadow-[0_0_15px_rgba(212,175,55,0.3)]" />
          </a>
        </Link>

        {/* Navigation */}
        <nav className="hidden md:flex items-center gap-8">
          {["PHILOSOPHY", "SYMBIOSIS", "JOIN COHORT 1"].map((item) => (
            <a 
              key={item}
              href={`#${item.toLowerCase().replace(/ /g, "-")}`}
              className="text-xs font-medium tracking-[0.2em] text-white/70 hover:text-nucleus-gold transition-colors duration-300 relative group"
            >
              {item}
              <span className="absolute -bottom-2 left-0 w-0 h-px bg-nucleus-gold transition-all duration-300 group-hover:w-full" />
            </a>
          ))}
        </nav>

        {/* CTA Button */}
        <button className="hidden md:block px-6 py-2 bg-white/5 hover:bg-nucleus-gold hover:text-nucleus-navy border border-white/20 hover:border-nucleus-gold rounded-full text-xs font-bold tracking-widest transition-all duration-300 backdrop-blur-sm">
          ACCESS
        </button>

        {/* Mobile Menu Toggle (Placeholder) */}
        <button className="md:hidden text-white">
          <div className="space-y-2">
            <div className="w-8 h-px bg-white" />
            <div className="w-8 h-px bg-white" />
          </div>
        </button>
      </div>
    </motion.header>
  );
}
