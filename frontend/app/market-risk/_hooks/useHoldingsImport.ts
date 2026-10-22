"use client";

import { useState } from "react";
import { api, type PortfolioImportResponse } from "@/lib/api";

const MAX_BYTES = 1_048_576; // 1 MB

export function useHoldingsImport() {
  const [isOpen, setIsOpen] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [result, setResult] = useState<PortfolioImportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  const reset = () => {
    setIsUploading(false);
    setResult(null);
    setError(null);
    setFileName(null);
  };

  const openModal = () => {
    reset();
    setIsOpen(true);
  };

  const closeModal = () => {
    setIsOpen(false);
  };

  const importFile = async (file: File) => {
    setError(null);
    setResult(null);
    setFileName(file.name);

    if (file.size > MAX_BYTES) {
      setError(`File size (${(file.size / 1024 / 1024).toFixed(2)} MB) exceeds the 1 MB limit.`);
      return;
    }

    setIsUploading(true);

    try {
      const text = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve((reader.result as string) || "");
        reader.onerror = () => reject(new Error("Failed to read file from browser"));
        reader.readAsText(file, "UTF-8");
      });

      const res = await api.market.importHoldings(text, file.name);
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to import holdings from CSV.");
    } finally {
      setIsUploading(false);
    }
  };

  return {
    isOpen,
    isUploading,
    result,
    error,
    fileName,
    openModal,
    closeModal,
    importFile,
    reset,
  };
}
