import { isAuthenticatd, signOut } from "@/lib/actions/auth.action";
import Image from "next/image";
import Link from "next/link";
import { redirect } from "next/navigation";
import React, { ReactNode } from "react";

const RootLayout = async ({ children }: { children: ReactNode }) => {
  const isUserAuthenticated = await isAuthenticatd();

  if (!isUserAuthenticated) redirect("/sign-up");

  return (
    <div className="root-layout">
      <nav className="flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2">
          <Image src="/logo.svg" alt="logo" width={38} height={32} />
          <h2 className="text-primary-100">AI Advisor</h2>
        </Link>
        {isUserAuthenticated && (
          <button
            onClick={signOut}
            className="signout-btn bg-red-500 text-white px-4 py-2 rounded ml-auto"
          >
            Sign Out
          </button>
        )}
      </nav>
      {children}
    </div>
  );
};

export default RootLayout;
