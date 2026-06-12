import { useState, useRef, useEffect } from 'react'
import './App.css'
import Message from './components/Message'
import InputBox from './components/InputBox'

const WELCOME_MESSAGE = {
  id: 0,
  role: 'assistant',
  content:
    '안녕하세요! 저는 **Wallet Guard**입니다.\n\n**온통청년**과 **금융감독원** 데이터를 기반으로 청년 정책 및 금융 상품 정보를 안내해 드립니다.\n\n궁금한 것을 편하게 물어보세요! 예시:\n• 청년 주거 지원 정책이 뭐가 있나요?\n• 2년 적금 금리 높은 상품 추천해주세요\n• 청년 취업 지원 프로그램 알려주세요\n• 정기예금 금리 비교해주세요',
  sources: [],
}

export default function App() {
  const [messages, setMessages] = useState([WELCOME_MESSAGE])
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  const sendMessage = async (text) => {
    const userMsg = {
      id: Date.now(),
      role: 'user',
      content: text,
      sources: [],
    }

    const historyForApi = messages
      .filter((m) => m.id !== 0)
      .map((m) => ({ role: m.role, content: m.content }))

    setMessages((prev) => [...prev, userMsg])
    setIsLoading(true)

    try {
      const res = await fetch('http://localhost:8000/api/chat/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, history: historyForApi }),
      })

      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()

      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: 'assistant',
          content: data.reply,
          sources: data.sources || [],
        },
      ])
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: 'assistant',
          content:
            '죄송합니다. 오류가 발생했습니다. 서버가 실행 중인지 확인해주세요.',
          sources: [],
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-inner">
          <div className="header-brand">
            <span className="brand-icon">🛡️</span>
            <div>
              <h1>Wallet Guard</h1>
              <p>청년 금융 &amp; 정책 정보 도우미</p>
            </div>
          </div>
          <div className="header-sources">
            <span className="src-badge src-ontong">온통청년</span>
            <span className="src-badge src-fss">금융감독원</span>
          </div>
        </div>
      </header>

      <div className="chat-body">
        <div className="messages-scroll">
          {messages.map((msg) => (
            <Message key={msg.id} message={msg} />
          ))}
          {isLoading && (
            <div className="msg-row assistant-row">
              <div className="avatar">🛡️</div>
              <div className="bubble assistant-bubble typing-bubble">
                <span className="dot" />
                <span className="dot" />
                <span className="dot" />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        <InputBox onSend={sendMessage} disabled={isLoading} />
      </div>
    </div>
  )
}
