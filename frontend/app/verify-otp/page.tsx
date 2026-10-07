"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Shield, Loader2, KeyRound } from "lucide-react";
import { authService } from "@/services/auth";
import { useAuthStore } from "@/stores/auth-store";

function VerifyOTPContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const setAuth = useAuthStore((state) => state.setAuth);
  
  const [identifier, setIdentifier] = useState("");
  const [otp, setOtp] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const ident = searchParams.get("identifier");
    if (ident) {
      setIdentifier(ident);
    }
  }, [searchParams]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const { access_token, user } = await authService.verifyOtp({ identifier, otp });
      
      setAuth(user, access_token);
      
      if (!user.display_name) {
        router.push("/onboarding");
      } else {
        router.push("/");
      }
    } catch (err: any) {
      setError(err.message || "Verification failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md p-8 rounded-2xl bg-gray-900 border border-gray-800 shadow-2xl">
      <div className="flex flex-col items-center mb-8">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-600 mb-4">
          <KeyRound className="h-6 w-6 text-white" />
        </div>
        <h1 className="text-2xl font-bold">Verify Phone</h1>
        <p className="text-gray-400 mt-2 text-sm text-center">
          Enter the 6-digit code sent to {identifier || "your device"}
          <br/>
          <span className="text-blue-400 text-xs mt-1 block">(Mock: use 123456)</span>
        </p>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-lg bg-red-900/50 border border-red-500/50 text-red-200 text-sm text-center">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Verification Code</label>
          <input
            type="text"
            required
            maxLength={6}
            value={otp}
            onChange={(e) => setOtp(e.target.value)}
            className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white placeholder-gray-500 text-center text-2xl tracking-[0.5em] font-mono transition-all"
            placeholder="000000"
          />
        </div>

        <button
          type="submit"
          disabled={loading || otp.length !== 6}
          className="w-full py-2.5 mt-4 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors flex items-center justify-center"
        >
          {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : "Verify & Continue"}
        </button>
      </form>
    </div>
  );
}

export default function VerifyOTPPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-4 bg-black text-white">
      <Suspense fallback={<div className="text-gray-400 flex flex-col items-center"><Loader2 className="h-8 w-8 animate-spin text-blue-500 mb-4" /> Loading verification...</div>}>
        <VerifyOTPContent />
      </Suspense>
    </main>
  );
}
