const imgGroup = "/icons/ultra-logo.svg";

export default function OnboardingLogo() {
  return (
    <div className="absolute left-8 top-8 z-10 rotate-90 pl-[20px]">
      <div className="h-[43px] w-[45px] relative">
        <img
          alt="Ultra Logo"
          className="block max-w-none size-full"
          src={imgGroup}
        />
      </div>
    </div>
  );
}
