import { useState, useCallback, useRef, useEffect } from "react";
import { ChatSidebar } from "@/components/ChatSidebar";
import { ChatMessage } from "@/components/ChatMessage";
import { ChatInput } from "@/components/ChatInput";
import { streamChat, generateImage, type Message, type MessageContent, getTextContent } from "@/lib/chat";
import { toast } from "sonner";
import { Sparkles, Menu, Image, Mic, MessageSquare, Code2, Presentation } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface Chat {
  id: string;
  title: string;
  messages: Message[];
}

function genId() {
  return Math.random().toString(36).slice(2, 10);
}

export default function Index() {
  const [chats, setChats] = useState<Chat[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const activeChat = chats.find((c) => c.id === activeId);
  const messages = activeChat?.messages ?? [];

  const scrollToBottom = useCallback(() => {
    setTimeout(() => {
      if (scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      }
    }, 50);
  }, []);

  useEffect(() => { scrollToBottom(); }, [messages, scrollToBottom]);

  const handleNew = useCallback(() => {
    const id = genId();
    setChats((prev) => [{ id, title: "Yeni Sohbet", messages: [] }, ...prev]);
    setActiveId(id);
    setSidebarOpen(false);
  }, []);

  const handleGenerateImage = useCallback(
    async (chatId: string, msgIndex: number, prompt: string) => {
      const result = await generateImage(prompt);
      if (result.error) { toast.error(result.error); return; }
      if (result.imageUrl) {
        setChats((prev) =>
          prev.map((c) => {
            if (c.id !== chatId) return c;
            const msgs = [...c.messages];
            const msg = msgs[msgIndex];
            if (msg) msgs[msgIndex] = { ...msg, images: [...(msg.images ?? []), result.imageUrl!] };
            return { ...c, messages: msgs };
          })
        );
      }
    }, []
  );

  const handleSend = useCallback(
    async (text: string, uploadedImages?: string[]) => {
      let chatId = activeId;
      if (!chatId) {
        chatId = genId();
        setChats((prev) => [{ id: chatId!, title: text.slice(0, 30) || "Görsel sohbet", messages: [] }, ...prev]);
        setActiveId(chatId);
      }

      let content: MessageContent;
      if (uploadedImages && uploadedImages.length > 0) {
        const parts: MessageContent = [];
        if (text) parts.push({ type: "text", text });
        uploadedImages.forEach((url) => parts.push({ type: "image_url", image_url: { url } }));
        content = parts;
      } else {
        content = text;
      }

      const userMsg: Message = { role: "user", content };

      setChats((prev) =>
        prev.map((c) => {
          if (c.id !== chatId) return c;
          const title = c.messages.length === 0 ? (text.slice(0, 30) || "Görsel sohbet") : c.title;
          return { ...c, title, messages: [...c.messages, userMsg] };
        })
      );

      setIsLoading(true);
      let assistantContent = "";
      const allMessages = [...(chats.find((c) => c.id === chatId)?.messages ?? []), userMsg];

      try {
        await streamChat({
          messages: allMessages,
          onDelta: (chunk) => {
            assistantContent += chunk;
            const currentContent = assistantContent;
            setChats((prev) =>
              prev.map((c) => {
                if (c.id !== chatId) return c;
                const msgs = [...c.messages];
                const last = msgs[msgs.length - 1];
                if (last?.role === "assistant") {
                  msgs[msgs.length - 1] = { ...last, content: currentContent };
                } else {
                  msgs.push({ role: "assistant", content: currentContent });
                }
                return { ...c, messages: msgs };
              })
            );
            scrollToBottom();
          },
          onDone: () => {
            setIsLoading(false);
            const match = assistantContent.match(/\[GENERATE_IMAGE:\s*(.+?)\]/);
            if (match && chatId) {
              setChats((prev) => {
                const chat = prev.find((c) => c.id === chatId);
                if (chat) handleGenerateImage(chatId!, chat.messages.length - 1, match[1]);
                return prev;
              });
            }
          },
          onError: (error) => { setIsLoading(false); toast.error(error); },
        });
      } catch {
        setIsLoading(false);
        toast.error("Bağlantı hatası oluştu");
      }
    },
    [activeId, chats, scrollToBottom, handleGenerateImage]
  );

  const isEmpty = messages.length === 0;

  const capabilities = [
    { icon: Code2, label: "Kod Yazarım", desc: "C++, Python, JS, Rust, Go... Her dilde uzmanım.", emoji: "💻" },
    { icon: Presentation, label: "Sunum Hazırlarım", desc: "Konuna özel görselli, profesyonel slide'lar.", emoji: "🎨" },
    { icon: Image, label: "Görsel Oluştururum", desc: "İstediğin görseli sıfırdan yaratırım.", emoji: "🖼️" },
    { icon: MessageSquare, label: "Her Soruya Cevap", desc: "Bilim, tarih, felsefe, günlük hayat... Sor yeter.", emoji: "🧠" },
  ];

  return (
    <div className="flex h-screen bg-background">
      <div className="hidden md:block">
        <ChatSidebar chats={chats} activeId={activeId} onSelect={(id) => setActiveId(id)} onNew={handleNew} />
      </div>

      <AnimatePresence>
        {sidebarOpen && (
          <>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="fixed inset-0 bg-foreground/20 backdrop-blur-sm z-40 md:hidden" onClick={() => setSidebarOpen(false)} />
            <motion.div initial={{ x: -260 }} animate={{ x: 0 }} exit={{ x: -260 }}
              transition={{ type: "spring", damping: 25, stiffness: 300 }} className="fixed left-0 top-0 z-50 md:hidden">
              <ChatSidebar chats={chats} activeId={activeId} onSelect={(id) => { setActiveId(id); setSidebarOpen(false); }} onNew={handleNew} />
            </motion.div>
          </>
        )}
      </AnimatePresence>

      <main className="flex-1 flex flex-col min-w-0">
        <header className="border-b border-border px-4 py-3 flex items-center gap-3 bg-card/50 backdrop-blur-sm">
          <button onClick={() => setSidebarOpen(true)} className="md:hidden p-1 rounded-lg hover:bg-muted transition-colors">
            <Menu className="w-5 h-5 text-muted-foreground" />
          </button>
          <h1 className="font-heading text-lg font-semibold text-foreground">Asistan</h1>
          <div className="flex items-center gap-1.5 ml-auto">
            {[
              { icon: Code2, label: "Kod" },
              { icon: Presentation, label: "Sunum" },
              { icon: Image, label: "Görsel" },
              { icon: Mic, label: "Ses" },
            ].map(({ icon: Icon, label }) => (
              <span key={label} className="hidden sm:flex items-center gap-1 text-[10px] text-muted-foreground bg-muted px-2 py-1 rounded-full">
                <Icon className="w-3 h-3" /> {label}
              </span>
            ))}
          </div>
        </header>

        <div ref={scrollRef} className="flex-1 overflow-y-auto">
          {isEmpty ? (
            <div className="h-full flex flex-col items-center justify-center px-6">
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }} className="max-w-xl w-full">
                {/* AI Avatar & Greeting */}
                <div className="flex items-start gap-4 mb-8">
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
                    className="w-12 h-12 rounded-2xl bg-primary/15 flex items-center justify-center shrink-0"
                  >
                    <Sparkles className="w-6 h-6 text-primary" />
                  </motion.div>
                  <div>
                    <motion.h2
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: 0.3 }}
                      className="font-heading text-2xl font-bold text-foreground mb-2"
                    >
                      Merhaba, hoş geldin! 👋
                    </motion.h2>
                    <motion.p
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: 0.5 }}
                      className="text-muted-foreground text-sm leading-relaxed"
                    >
                      Ben senin yapay zeka asistanınım. Buraya geldiğin için çok memnunum!
                      Sana birçok konuda yardımcı olabilirim. İşte yapabileceklerimden bazıları:
                    </motion.p>
                  </div>
                </div>

                {/* Capabilities */}
                <div className="space-y-2.5">
                  {capabilities.map(({ icon: Icon, label, desc, emoji }, i) => (
                    <motion.div
                      key={label}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.6 + i * 0.12 }}
                      className="flex items-center gap-3 p-3.5 rounded-xl border border-border bg-card/60 hover:bg-muted/40 transition-colors cursor-default"
                    >
                      <span className="text-lg">{emoji}</span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-foreground">{label}</p>
                        <p className="text-xs text-muted-foreground">{desc}</p>
                      </div>
                      <Icon className="w-4 h-4 text-muted-foreground/40 shrink-0" />
                    </motion.div>
                  ))}
                </div>

                {/* Prompt */}
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 1.2 }}
                  className="text-center text-muted-foreground text-xs mt-6"
                >
                  Aşağıya bir mesaj yazarak başlayabilirsin ↓
                </motion.p>
              </motion.div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto divide-y divide-border/50">
              {messages.map((msg, i) => (
                <ChatMessage key={i} message={msg}
                  onGenerateImage={msg.role === "assistant" && activeId ? (prompt) => handleGenerateImage(activeId!, i, prompt) : undefined} />
              ))}
              {isLoading && messages[messages.length - 1]?.role !== "assistant" && (
                <div className="flex gap-3 py-5 px-4 md:px-0">
                  <div className="w-8 h-8 rounded-full bg-chat-ai border border-chat-ai-border flex items-center justify-center">
                    <div className="flex gap-1">
                      <span className="w-1.5 h-1.5 bg-muted-foreground/50 rounded-full animate-bounce [animation-delay:0ms]" />
                      <span className="w-1.5 h-1.5 bg-muted-foreground/50 rounded-full animate-bounce [animation-delay:150ms]" />
                      <span className="w-1.5 h-1.5 bg-muted-foreground/50 rounded-full animate-bounce [animation-delay:300ms]" />
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="border-t border-border bg-background/80 backdrop-blur-sm px-4 py-4">
          <div className="max-w-3xl mx-auto">
            <ChatInput onSend={handleSend} disabled={isLoading} />
            <p className="text-[11px] text-muted-foreground text-center mt-2.5">
              Kod • Sunum • Görsel • Ses — AI hata yapabilir, önemli bilgileri doğrulayın.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
