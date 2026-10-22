"use client";

import { useState, useRef, useEffect } from "react";
import {
  Bot,
  User,
  Send,
  Zap,
  Sparkles,
  AlertTriangle,
  FileText,
  Shield,
  RotateCcw,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Clock,
} from "lucide-react";
import MarkdownLite from "@/components/MarkdownLite";
import { api, CopilotResponse } from "@/lib/api";

function getFormattedTime(): string {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

let counter = 0;
function createMessageId(prefix: string): string {
  counter += 1;
  return `${prefix}_${counter}`;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  intent?: string;
  tool_trace?: CopilotResponse["tool_trace"];
  citations?: CopilotResponse["citations"];
  provenance_flags?: CopilotResponse["provenance_flags"];
  offline_fallback_mode?: boolean;
  safety_disclaimer?: string;
  timestamp: string;
}

const STARTER_PROMPTS = [
  {
    label: "Calculate Loan EMI",
    prompt: "Calculate EMI for a loan of ₹5,00,000 at 8.5% interest for 3 years.",
    category: "Loan Affordability",
  },
  {
    label: "Personal Stress Test",
    prompt: "Personal stress test: Monthly income ₹80,000, essential expenses ₹35,000, existing EMIs ₹12,000, liquid savings ₹1,50,000 under a 20% income reduction.",
    category: "Financial Stress",
  },
  {
    label: "Basel VaR Framework",
    prompt: "Explain the Basel supervisory backtesting traffic light zones for Value-at-Risk models.",
    category: "Regulatory RAG",
  },
  {
    label: "Market Risk Analysis",
    prompt: "Analyze market risk and VaR for a portfolio with 60% SPY and 40% AAPL.",
    category: "Market Risk",
  },
  {
    label: "Compare VaR Models",
    prompt: "Compare VaR models for equal weight spy and msft.",
    category: "Model Validation",
  },
  {
    label: "Replay Market Events",
    prompt: "Replay covid and the adani sell-off on my portfolio of 60% reliance and 40% tcs.",
    category: "Stress Replay",
  },
  {
    label: "Reverse Stress",
    prompt: "Reverse stress my portfolio of 50% spy and 50% msft: what market fall gives a 20% loss?",
    category: "Reverse Stress",
  },
];

export default function RiskCopilotPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Welcome to the **RiskWise Agentic Copilot**. I route your risk analysis queries through a bounded LangGraph state machine with deterministic domain tools and grounded retrieval from official regulatory sources.\n\nAsk for loan calculations, stress tests, market risk backtesting, or regulatory guidance.",
      timestamp: "Active",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedTraces, setExpandedTraces] = useState<Record<string, boolean>>({});

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const toggleTrace = (msgId: string) => {
    setExpandedTraces((prev) => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  const handleSend = async (messageText?: string) => {
    const textToSend = messageText || input;
    if (!textToSend.trim() || loading) return;

    const userMsgId = createMessageId("user");
    const userMessage: ChatMessage = {
      id: userMsgId,
      role: "user",
      content: textToSend.trim(),
      timestamp: getFormattedTime(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setError(null);
    setLoading(true);

    try {
      const response = await api.copilot.message(textToSend.trim());

      const assistantMsgId = createMessageId("assistant");
      const assistantMessage: ChatMessage = {
        id: assistantMsgId,
        role: "assistant",
        content: response.answer,
        intent: response.intent,
        tool_trace: response.tool_trace,
        citations: response.citations,
        provenance_flags: response.provenance_flags,
        offline_fallback_mode: response.offline_fallback_mode,
        safety_disclaimer: response.safety_disclaimer,
        timestamp: getFormattedTime(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
      // Auto-expand trace if tool ran
      if (response.tool_trace && response.tool_trace.length > 0) {
        setExpandedTraces((prev) => ({ ...prev, [assistantMsgId]: true }));
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to execute copilot query.");
    } finally {
      setLoading(false);
      setTimeout(() => textareaRef.current?.focus(), 100);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleReset = () => {
    setMessages([
      {
        id: `welcome_${Date.now()}`,
        role: "assistant",
        content:
          "Conversation restarted. Ask for loan calculations, stress tests, market risk backtesting, or regulatory guidance.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      },
    ]);
    setError(null);
  };

  return (
    <div className="min-h-[calc(100vh-10rem)] flex flex-col justify-between">
      <div className="max-w-5xl mx-auto w-full flex-1 flex flex-col space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-blue-500/10 border border-blue-500/30 text-blue-600 dark:text-blue-400">
              <Bot className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">Agentic Risk Copilot</h1>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/30">
                  LangGraph Bounded
                </span>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Deterministic calculation tools with grounded citations from official regulatory sources.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleReset}
              className="px-3 py-1.5 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-slate-400 dark:hover:border-slate-700 text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white text-xs font-medium flex items-center gap-1.5 transition cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              New Chat
            </button>
          </div>
        </div>

        {/* Starter Prompt Chips */}
        {messages.length <= 1 && (
          <div className="space-y-2">
            <div className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
              Suggested Scenarios
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {STARTER_PROMPTS.map((starter, i) => (
                <button
                  key={i}
                  onClick={() => handleSend(starter.prompt)}
                  className="p-3 rounded-xl text-left bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 hover:border-blue-500/50 hover:bg-slate-100 dark:hover:bg-slate-900 transition-all text-xs space-y-1 group cursor-pointer"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-800 dark:text-slate-200 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                      {starter.label}
                    </span>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400">
                      {starter.category}
                    </span>
                  </div>
                  <p className="text-slate-500 dark:text-slate-400 line-clamp-2 text-[11px]">{starter.prompt}</p>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Messages Stream */}
        <div className="flex-1 space-y-4 overflow-y-auto pr-1">
          {messages.map((msg) => {
            const isUser = msg.role === "user";
            const isTraceExpanded = expandedTraces[msg.id];

            return (
              <div
                key={msg.id}
                className={`flex gap-3 text-sm ${isUser ? "justify-end" : "justify-start"} animate-fade-in`}
              >
                {!isUser && (
                  <div className="w-8 h-8 rounded-xl bg-blue-600/20 border border-blue-500/30 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0 mt-0.5">
                    <Bot className="w-4 h-4" />
                  </div>
                )}

                <div
                  className={`max-w-2xl rounded-2xl p-4 space-y-3 ${
                    isUser
                      ? "bg-blue-600 text-white rounded-br-none"
                      : "bg-white dark:bg-slate-900/90 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 rounded-bl-none shadow-sm"
                  }`}
                >
                  {/* Message Header for Assistant */}
                  {!isUser && msg.intent && (
                    <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-2 text-xs">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[10px] uppercase px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-blue-600 dark:text-blue-400 border border-slate-300 dark:border-slate-700">
                          {msg.intent}
                        </span>
                        {msg.offline_fallback_mode && (
                          <span className="text-[10px] text-slate-500">Offline deterministic</span>
                        )}
                      </div>
                      <span className="text-[10px] text-slate-500 flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {msg.timestamp}
                      </span>
                    </div>
                  )}

                  {/* Body Content */}
                  {isUser ? (
                    <div className="leading-relaxed whitespace-pre-wrap">{msg.content}</div>
                  ) : (
                    <div className="text-xs leading-relaxed">
                      <MarkdownLite source={msg.content} />
                    </div>
                  )}

                  {/* Figures the guard removed because nothing computed them */}
                  {!isUser && msg.provenance_flags && msg.provenance_flags.length > 0 && (
                    <div role="alert" className="rounded-xl border border-amber-300 dark:border-amber-800/50 bg-amber-50 dark:bg-amber-950/30 p-3 text-xs text-amber-900 dark:text-amber-200 space-y-1">
                      <div className="font-semibold">
                        {msg.provenance_flags.length} figure{msg.provenance_flags.length === 1 ? "" : "s"} removed
                      </div>
                      <p className="text-amber-700 dark:text-amber-300/80">
                        Every number in a reply must come from a tool result, a cited source or your own message. These had no source:
                      </p>
                      <ul className="list-disc list-inside text-amber-700 dark:text-amber-300/80 font-mono">
                        {msg.provenance_flags.map((f, i) => (
                          <li key={i}>{f.token}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Deterministic Tool Execution Trace */}
                  {!isUser && msg.tool_trace && msg.tool_trace.length > 0 && (
                    <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-100 dark:bg-slate-950/70 overflow-hidden text-xs">
                      <button
                        onClick={() => toggleTrace(msg.id)}
                        className="w-full px-3 py-2 flex items-center justify-between text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-900/50 transition cursor-pointer"
                      >
                        <div className="flex items-center gap-2">
                          <Zap className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
                          <span className="font-semibold text-[11px] font-mono">
                            Tool Execution: {msg.tool_trace.map((t) => t.tool_name).join(", ")}
                          </span>
                          {msg.tool_trace.every((t) => t.is_authoritative) && (
                            <span className="text-[9px] px-1.5 py-0.2 rounded bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 border border-emerald-300 dark:border-emerald-800/40 font-mono">
                              Authoritative
                            </span>
                          )}
                        </div>
                        {isTraceExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                      </button>

                      {isTraceExpanded && (
                        <div className="p-3 border-t border-slate-200 dark:border-slate-800 space-y-2 font-mono text-[11px] bg-slate-100 dark:bg-slate-950/90">
                          {msg.tool_trace.map((t, i) => (
                            <div key={`${t.tool_name}-${i}`} className="space-y-2">
                              {msg.tool_trace!.length > 1 && <div className="text-slate-700 dark:text-slate-300 font-semibold">{t.tool_name}</div>}
                              <div>
                                <span className="text-slate-500 block mb-0.5">Parameters:</span>
                                <pre className="bg-white dark:bg-slate-900 p-2 rounded border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 overflow-x-auto max-h-48">
                                  {JSON.stringify(t.arguments, null, 2)}
                                </pre>
                              </div>
                              <div>
                                <span className="text-slate-500 block mb-0.5">Authoritative Engine Output:</span>
                                <pre className="bg-white dark:bg-slate-900 p-2 rounded border border-slate-200 dark:border-slate-800 text-emerald-600 dark:text-emerald-400 overflow-x-auto max-h-64">
                                  {JSON.stringify(t.output, null, 2)}
                                </pre>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Grounded Citations */}
                  {!isUser && msg.citations && msg.citations.length > 0 && (
                    <div className="rounded-xl border border-slate-200 dark:border-slate-800/80 bg-slate-100 dark:bg-slate-950/50 p-3 space-y-2 text-xs">
                      <div className="font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1.5 text-[11px]">
                        <FileText className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                        Grounded Source Citations ({msg.citations.length})
                      </div>
                      <div className="space-y-1.5">
                        {msg.citations.map((c, idx) => (
                          <div key={idx} className="p-2 rounded-lg bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800/60 text-[11px]">
                            <div className="flex items-center justify-between text-slate-800 dark:text-slate-200 font-medium">
                              <span>{c.title}</span>
                              <span className="text-[10px] text-slate-500">{c.publisher}</span>
                            </div>
                            {c.snippet && <p className="text-slate-500 dark:text-slate-400 text-[10px] mt-1 line-clamp-2">{c.snippet}</p>}
                            {c.url && (
                              <a
                                href={c.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-[10px] text-blue-600 dark:text-blue-400 hover:underline mt-1"
                              >
                                View official source <ExternalLink className="w-2.5 h-2.5" />
                              </a>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Safety Disclaimer */}
                  {!isUser && msg.safety_disclaimer && (
                    <div className="text-[10px] text-slate-500 border-t border-slate-200 dark:border-slate-800/60 pt-2 flex items-start gap-1.5">
                      <Shield className="w-3 h-3 text-slate-500 shrink-0 mt-0.5" />
                      <span>{msg.safety_disclaimer}</span>
                    </div>
                  )}
                </div>

                {isUser && (
                  <div className="w-8 h-8 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 flex items-center justify-center shrink-0 mt-0.5">
                    <User className="w-4 h-4" />
                  </div>
                )}
              </div>
            );
          })}

          {/* Loading Indicator */}
          {loading && (
            <div className="flex gap-3 text-sm justify-start animate-fade-in">
              <div className="w-8 h-8 rounded-xl bg-blue-600/20 border border-blue-500/30 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4 animate-pulse" />
              </div>
              <div className="bg-white dark:bg-slate-900/90 border border-slate-200 dark:border-slate-800 rounded-2xl rounded-bl-none p-4 space-y-2">
                <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                  <div className="w-2 h-2 rounded-full bg-blue-400 animate-ping" />
                  <span>Evaluating state graph & executing domain engines...</span>
                </div>
              </div>
            </div>
          )}

          {/* Error Alert */}
          {error && (
            <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-300 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-xs flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 text-rose-600 dark:text-rose-400" />
                <span>{error}</span>
              </div>
              <button
                onClick={() => handleSend()}
                className="px-2.5 py-1 rounded bg-rose-600 dark:bg-rose-900/60 hover:bg-rose-700 dark:hover:bg-rose-900 text-white font-medium text-[11px] transition cursor-pointer"
              >
                Retry
              </button>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-3 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 focus-within:border-blue-500/60 transition-colors shadow-lg">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-end gap-2"
          >
            <textarea
              ref={textareaRef}
              rows={2}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask the risk copilot (e.g., 'Calculate EMI for ₹10L at 9.25% for 5 years' or 'Explain Basel green zone')..."
              disabled={loading}
              className="flex-1 bg-transparent border-0 text-sm text-slate-900 dark:text-slate-100 placeholder-slate-500 focus:outline-none resize-none px-2 py-1"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="p-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:hover:bg-blue-600 text-white transition shadow-md shadow-blue-600/20 cursor-pointer shrink-0"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
          <div className="flex items-center justify-between text-[10px] text-slate-500 px-2 pt-2 border-t border-slate-200 dark:border-slate-800/60 mt-1">
            <span>Deterministic LangGraph agent · Grounded regulatory citations · Press Enter to send</span>
            <span>RiskWise Copilot v3.0</span>
          </div>
        </div>
      </div>
    </div>
  );
}
