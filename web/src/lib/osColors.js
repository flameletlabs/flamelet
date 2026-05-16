export const OS_COLORS = {
  Linux:   { color: '#4493f8', label: 'Linux' },
  FreeBSD: { color: '#cd7b6a', label: 'FreeBSD' },
  OpenBSD: { color: '#e3b341', label: 'OpenBSD' },
}

export function osBullets(supportedOs) {
  return ['Linux', 'FreeBSD', 'OpenBSD'].map(os => ({
    os,
    supported: supportedOs.includes(os),
    color: OS_COLORS[os].color,
  }))
}
