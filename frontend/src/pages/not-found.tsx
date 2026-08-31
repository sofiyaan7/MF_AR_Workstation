import { Compass, Home } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/states";

export function NotFoundPage() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <EmptyState
        icon={Compass}
        title="Page not found"
        description="That page does not exist, or you do not have access to it."
        action={
          <Button asChild>
            <Link to="/">
              <Home />
              Back to dashboard
            </Link>
          </Button>
        }
        className="border-none bg-transparent"
      />
    </div>
  );
}
