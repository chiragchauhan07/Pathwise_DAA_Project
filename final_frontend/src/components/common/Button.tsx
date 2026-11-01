import type { ButtonHTMLAttributes, Ref } from 'react';

type Variant = 'primary' | 'secondary' | 'quiet';

export function Button({
  variant = 'secondary', small, className = '', ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; small?: boolean; ref?: Ref<HTMLButtonElement> }) {
  const cls = ['btn', variant === 'primary' ? 'btn-primary' : variant === 'quiet' ? 'btn-quiet' : '', small ? 'btn-sm' : '', className].filter(Boolean).join(' ');
  return <button type="button" {...rest} className={cls} />;
}
