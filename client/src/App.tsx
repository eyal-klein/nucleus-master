import { Switch, Route } from "wouter";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "./lib/queryClient";
import { Toaster } from "@/components/ui/sonner";
import Home from "@/pages/Home";
import NotFound from "@/pages/not-found";
import { motion } from "framer-motion";

function Header() {
  return (
    <motion.header 
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8, ease: "easeOut" }}
      className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 py-4 md:px-12 bg-background/80 backdrop-blur-md border-b border-border/20"
    >
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-nucleus-gold to-nucleus-cyan opacity-80" />
        <span className="font-serif text-xl font-bold tracking-widest text-foreground">NUCLEUS</span>
      </div>
      <nav className="hidden md:flex items-center gap-8">
        <a href="#philosophy" className="text-sm font-medium text-muted-foreground hover:text-nucleus-gold transition-colors">PHILOSOPHY</a>
        <a href="#symbiosis" className="text-sm font-medium text-muted-foreground hover:text-nucleus-gold transition-colors">SYMBIOSIS</a>
        <a href="#join" className="text-sm font-medium text-muted-foreground hover:text-nucleus-gold transition-colors">JOIN COHORT 1</a>
      </nav>
      <button className="px-6 py-2 text-xs font-bold tracking-widest text-background bg-foreground hover:bg-nucleus-gold transition-colors rounded-full">
        ACCESS
      </button>
    </motion.header>
  );
}

function Footer() {
  return (
    <footer className="py-12 px-6 md:px-12 bg-nucleus-navy text-white border-t border-white/10">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-8">
        <div className="flex flex-col items-center md:items-start gap-2">
          <span className="font-serif text-2xl font-bold tracking-widest">NUCLEUS</span>
          <p className="text-xs text-white/60 tracking-wider">WE 2.0 AT MAXIMUM THRIVE</p>
        </div>
        <div className="flex gap-8 text-xs text-white/60">
          <a href="#" className="hover:text-nucleus-cyan transition-colors">PRIVACY</a>
          <a href="#" className="hover:text-nucleus-cyan transition-colors">TERMS</a>
          <a href="#" className="hover:text-nucleus-cyan transition-colors">CONTACT</a>
        </div>
        <div className="text-xs text-white/40">
          © 2025 NUCLEUS. ALL RIGHTS RESERVED.
        </div>
      </div>
    </footer>
  );
}

function Router() {
  return (
    <div className="min-h-screen flex flex-col font-sans bg-background text-foreground selection:bg-nucleus-gold/30">
      <Header />
      <main className="flex-grow pt-20">
        <Switch>
          <Route path="/" component={Home} />
          <Route component={NotFound} />
        </Switch>
      </main>
      <Footer />
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router />
      <Toaster />
    </QueryClientProvider>
  );
}

export default App;
