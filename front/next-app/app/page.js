"use client"

import dynamic from 'next/dynamic';
import {useEffect} from "react"
const MapWithNoSSR = dynamic(() => import('../components/MapComponent'), {
  ssr: false
});



export default function Home() {
  return (
    <div>
      <h1>карта марадеров</h1>
      <MapWithNoSSR />
    </div>
  );
}
