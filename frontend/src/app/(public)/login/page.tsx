"use client";

import React from "react";
import { EnterpriseLoginForm } from "@/components/auth/EnterpriseLoginForm";

export default function LoginPage() {
  return (
    <div className="flex-1 flex items-center justify-center py-10 px-4 sm:px-6 lg:px-8">
      <EnterpriseLoginForm onSuccessRedirect="/dashboard" standalone={false} />
    </div>
  );
}
