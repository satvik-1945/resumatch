import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "Outreach sessions · Resumatch", description: "A little outreach. Real progress. Your private activity log.",
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}
