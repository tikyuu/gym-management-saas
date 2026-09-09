export const devConfig = {
  applicationName: "gym-management",
  environmentName: "dev",
  region: "ap-northeast-1",
  vpcCidr: "10.10.0.0/16",
  publicSubnets: [
    {
      id: "PublicSubnet1",
      name: "public-1a-subnet",
      availabilityZone: "ap-northeast-1a",
      cidrBlock: "10.10.1.0/24",
    },
    {
      id: "PublicSubnet2",
      name: "public-1c-subnet",
      availabilityZone: "ap-northeast-1c",
      cidrBlock: "10.10.2.0/24",
    },
  ],
  privateIngressSubnets: [
    {
      id: "PrivateIngressSubnet1",
      name: "private-ingress-1a-subnet",
      availabilityZone: "ap-northeast-1a",
      cidrBlock: "10.10.11.0/24",
    },
    {
      id: "PrivateIngressSubnet2",
      name: "private-ingress-1c-subnet",
      availabilityZone: "ap-northeast-1c",
      cidrBlock: "10.10.12.0/24",
    },
  ],
};
