"use client";

import { useState } from "react";
import { Upload, FileText, Search, Loader2 } from "lucide-react";
import toast from "react-hot-toast";
import api from "@/lib/api";

type SearchResult = {
  content: string;
  source: string;
  page?: number;
};

export default function DocumentsPage() {
  const [file, setFile] = useState<File | null>(null);
  const [subject, setSubject] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("subject", subject || "General");

    try {
      const res = await api.post("/docs/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast.success(res.data.message);
      setFile(null);
      setSubject("");
    } catch (error) {
      toast.error("Failed to upload document");
    } finally {
      setIsUploading(false);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    try {
      const res = await api.get(`/docs/search?q=${encodeURIComponent(searchQuery)}`);
      setResults(res.data);
      if (res.data.length === 0) toast("No results found", { icon: "ℹ️" });
    } catch (error) {
      toast.error("Failed to search documents");
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="p-8 space-y-8 h-full overflow-y-auto">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white">Documents</h1>
        <p className="text-gray-400 mt-2">Upload notes to enrich AURA's knowledge base.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Upload Section */}
        <div className="glass-panel p-6 rounded-2xl">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center">
            <Upload className="w-5 h-5 mr-2 text-primary" />
            Upload New Document
          </h2>
          <form onSubmit={handleUpload} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-2">File (PDF/TXT)</label>
              <input
                type="file"
                accept=".pdf,.txt,.md"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="block w-full text-sm text-gray-400
                  file:mr-4 file:py-2 file:px-4
                  file:rounded-xl file:border-0
                  file:text-sm file:font-semibold
                  file:bg-primary/20 file:text-primary
                  hover:file:bg-primary/30 file:transition-colors
                  cursor-pointer bg-surface/50 rounded-xl p-2 border border-border"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-2">Subject (Optional)</label>
              <input
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="e.g. DBMS, Data Structures"
                className="w-full bg-surface border border-border rounded-xl px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
            </div>
            <button
              type="submit"
              disabled={!file || isUploading}
              className="w-full bg-primary hover:bg-primary-hover text-white rounded-xl px-4 py-2.5 font-medium transition-colors disabled:opacity-50 flex items-center justify-center"
            >
              {isUploading ? <Loader2 className="w-5 h-5 animate-spin" /> : "Upload to AURA"}
            </button>
          </form>
        </div>

        {/* Search Section */}
        <div className="glass-panel p-6 rounded-2xl flex flex-col">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center">
            <Search className="w-5 h-5 mr-2 text-primary" />
            Search Knowledge Base
          </h2>
          <form onSubmit={handleSearch} className="relative mb-6">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search your notes..."
              className="w-full bg-surface border border-border rounded-xl px-4 py-2.5 pl-10 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <button
              type="submit"
              disabled={!searchQuery.trim() || isSearching}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 bg-primary/20 hover:bg-primary/30 text-primary rounded-lg transition-colors disabled:opacity-50"
            >
              {isSearching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            </button>
          </form>

          <div className="flex-1 overflow-y-auto space-y-3">
            {results.length > 0 ? (
              results.map((res, i) => (
                <div key={i} className="bg-surface/50 border border-white/5 rounded-xl p-4">
                  <div className="flex items-center space-x-2 mb-2 text-primary text-xs font-medium uppercase tracking-wider">
                    <FileText className="w-3 h-3" />
                    <span>{res.source} {res.page ? `(Pg ${res.page})` : ""}</span>
                  </div>
                  <p className="text-sm text-gray-300 line-clamp-3 leading-relaxed">
                    "{res.content}"
                  </p>
                </div>
              ))
            ) : (
              <div className="h-32 flex flex-col items-center justify-center text-gray-500">
                <FileText className="w-8 h-8 opacity-20 mb-2" />
                <p className="text-sm">Search results will appear here</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
