import { redirect } from "next/navigation"

export default function Page() {
  // single audio section: redirect to audio search page
  redirect("/audio-search")
}
