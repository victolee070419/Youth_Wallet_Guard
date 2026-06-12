import { useState, useRef } from 'react'
import './InputBox.css'

const SUGGESTIONS = [
  '청년 주거 지원 정책',
  '금리 높은 적금 추천',
  '청년 창업 지원',
  '정기예금 비교',
  '취업 지원 프로그램',
]

export default function InputBox({ onSend, disabled }) {
  const [text, setText] = useState('')
  const ref = useRef(null)

  const submit = () => {
    const trimmed = text.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setText('')
    ref.current?.style && (ref.current.style.height = 'auto')
    ref.current?.focus()
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  const autoResize = (e) => {
    e.target.style.height = 'auto'
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'
  }

  return (
    <div className="input-area">
      <div className="suggestions">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            className="suggestion-btn"
            disabled={disabled}
            onClick={() => {
              if (!disabled) {
                setText(s)
                ref.current?.focus()
              }
            }}
          >
            {s}
          </button>
        ))}
      </div>

      <div className="input-row">
        <textarea
          ref={ref}
          value={text}
          onChange={(e) => {
            setText(e.target.value)
            autoResize(e)
          }}
          onKeyDown={handleKey}
          placeholder="청년 정책이나 금융 상품에 대해 물어보세요… (Enter 전송)"
          rows={1}
          disabled={disabled}
        />
        <button
          className={`send-btn${!text.trim() || disabled ? ' send-disabled' : ''}`}
          onClick={submit}
          disabled={!text.trim() || disabled}
          aria-label="전송"
        >
          ↑
        </button>
      </div>
    </div>
  )
}
