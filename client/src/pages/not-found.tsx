import { Link } from "wouter";
import { AlertCircle } from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-[80vh] flex items-center justify-center bg-background">
      <div className="text-center space-y-6 p-8 max-w-md">
        <div className="flex justify-center">
          <AlertCircle className="h-16 w-16 text-nucleus-gold opacity-80" />
        </div>
        <h1 className="font-serif text-4xl font-bold text-foreground">404</h1>
        <p className="text-muted-foreground font-medium">
          The sequence you are looking for does not exist in this organism.
        </p>
        <Link href="/">
          <a className="inline-block px-8 py-3 text-sm font-bold tracking-widest text-background bg-foreground hover:bg-nucleus-gold transition-colors rounded-full">
            RETURN TO CORE
          </a>
        </Link>
      </div>
    </div>
  );
}
