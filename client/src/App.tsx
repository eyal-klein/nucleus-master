import { Switch, Route } from "wouter";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "./lib/queryClient";
import { Toaster } from "@/components/ui/sonner";
import Home from "@/pages/Home";
import NotFound from "@/pages/not-found";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";

function Router() {
  return (
    <div className="min-h-screen flex flex-col font-sans bg-nucleus-navy text-white selection:bg-nucleus-gold/30">
      <Header />
      <main className="flex-grow">
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
