"use client";

"use client";

import Link from "next/link";
import React from "react";

const TDEEButton = () => {
  return (
    <Link
      href="/tdee"
      className="signin-btn bg-blue-500 text-white px-4 py-2 rounded ml-auto"
    >
      TDEE Calculator
    </Link>
  );
};

export default TDEEButton;
