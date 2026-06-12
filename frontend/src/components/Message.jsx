import '../App.css'

const CHIP_CLASS = {
  ontong: 'chip-ontong',
  fss: 'chip-fss',
}

function renderText(text) {
  const lines = text.split('\n')
  return lines.map((line, i) => {
    const parts = line.split(/\*\*(.*?)\*\*/g)
    const nodes = parts.map((part, j) =>
      j % 2 === 1 ? <strong key={j}>{part}</strong> : part,
    )
    return (
      <span key={i}>
        {nodes}
        {i < lines.length - 1 && <br />}
      </span>
    )
  })
}

export default function Message({ message }) {
  const isUser = message.role === 'user'

  return (
    <div className={`msg-row ${isUser ? 'user-row' : 'assistant-row'}`}>
      <div className={`avatar ${isUser ? 'user-avatar' : ''}`}>
        {isUser ? '나' : '🛡️'}
      </div>

      <div>
        <div className={`bubble ${isUser ? 'user-bubble' : 'assistant-bubble'}`}>
          {renderText(message.content)}
        </div>

        {!isUser && message.sources?.length > 0 && (
          <div className="sources">
            <span className="sources-label">출처:</span>
            {message.sources.map((src, i) => (
              <span
                key={i}
                className={`source-chip ${CHIP_CLASS[src.type] ?? ''}`}
              >
                {src.name}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
