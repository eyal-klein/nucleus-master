import { Link } from "wouter";

export function Footer() {
  return (
    <footer className="bg-nucleus-navy border-t border-white/5 py-20 relative overflow-hidden">
      {/* Background Ambient */}
      <div className="absolute inset-0 bg-[url('/images/noise.png')] opacity-5 mix-blend-overlay pointer-events-none" />
      
      <div className="max-w-7xl mx-auto px-6 relative z-10">
        <div className="flex flex-col md:flex-row justify-between items-center gap-12">
          
          {/* Brand Column */}
          <div className="text-center md:text-left space-y-6">
            <img 
              src="/images/nucleus_logo_on_dark.png" 
              alt="NUCLEUS" 
              className="h-16 w-auto mx-auto md:mx-0 opacity-80 grayscale hover:grayscale-0 transition-all duration-700"
            />
            <p className="text-xs tracking-[0.3em] text-nucleus-cyan uppercase font-medium">
              WE 2.0 AT MAXIMUM THRIVE
            </p>
          </div>

          {/* Links */}
          <div className="flex gap-8 md:gap-12">
            {["PRIVACY", "TERMS", "CONTACT"].map((item) => (
              <a 
                key={item}
                href="#" 
                className="text-[10px] tracking-[0.2em] text-white/40 hover:text-nucleus-gold transition-colors duration-300"
              >
                {item}
              </a>
            ))}
          </div>
        </div>

        <div className="mt-20 pt-8 border-t border-white/5 flex flex-col md:flex-row justify-between items-center gap-4 text-[10px] text-white/20 tracking-widest">
          <p>© 2025 NUCLEUS. ALL RIGHTS RESERVED.</p>
          <p>DESIGNED FOR SYMBIOSIS.</p>
        </div>
      </div>
    </footer>
  );
}
