
/* Ceph-P4-Booster */
#include <core.p4>
#include <v1model.p4>
typedef bit<48> macAddr_t;
typedef bit<9> egressSpec_t;
header ethernet_t { macAddr_t dstAddr; macAddr_t srcAddr; bit<16> etherType; }
header ipv4_t { bit<4> version; bit<4> ihl; bit<8> diffserv; bit<16> totalLen; bit<16> identification; bit<3> flags; bit<13> fragOffset; bit<8> ttl; bit<8> protocol; bit<16> hdrChecksum; bit<32> srcAddr; bit<32> dstAddr; }
header tcp_t { bit<16> srcPort; bit<16> dstPort; bit<32> seqNo; bit<32> ackNo; bit<4> dataOffset; bit<4> res; bit<8> flags; bit<16> window; bit<16> checksum; bit<16> urgentPtr; }
header udp_t { bit<16> srcPort; bit<16> dstPort; bit<16> len; bit<16> checksum; }
struct headers { ethernet_t ethernet; ipv4_t ipv4; tcp_t tcp; udp_t udp; }
struct metadata { }
parser MyParser(packet_in packet, out headers hdr, inout metadata meta, inout standard_metadata_t standard_metadata) {
    state start { transition parse_ethernet; }
    state parse_ethernet { packet.extract(hdr.ethernet); transition select(hdr.ethernet.etherType) { 0x0800: parse_ipv4; default: accept; } }
    state parse_ipv4 { packet.extract(hdr.ipv4); transition select(hdr.ipv4.protocol) { 6: parse_tcp; 17: parse_udp; default: accept; } }
    state parse_tcp { packet.extract(hdr.tcp); transition accept; }
    state parse_udp { packet.extract(hdr.udp); transition accept; }
}
control MyIngress(inout headers hdr, inout metadata meta, inout standard_metadata_t standard_metadata) {
    action drop() { mark_to_drop(standard_metadata); }
    action ipv4_forward(macAddr_t dstAddr, egressSpec_t port) {
        standard_metadata.egress_spec = port;
        hdr.ethernet.srcAddr = hdr.ethernet.dstAddr;
        hdr.ethernet.dstAddr = dstAddr;
        hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
    }
    table ipv4_lpm { key = { hdr.ipv4.dstAddr: lpm; } actions = { ipv4_forward; drop; } size = 1024; default_action = drop(); }
    apply { if (hdr.ipv4.isValid()) { ipv4_lpm.apply(); } }
}
control MyEgress(inout headers hdr, inout metadata meta, inout standard_metadata_t standard_metadata) {
    apply {
        if (standard_metadata.instance_type == 1) { 
             hdr.ethernet.srcAddr = hdr.ethernet.dstAddr;
             if (hdr.ipv4.dstAddr == 0x0a000001) { hdr.ethernet.dstAddr = 0x00000a000001; }
             else if (hdr.ipv4.dstAddr == 0x0a000002) { hdr.ethernet.dstAddr = 0x00000a000002; }
             else if (hdr.ipv4.dstAddr == 0x0a000003) { hdr.ethernet.dstAddr = 0x00000a000003; }
        }
    }
}
control MyComputeChecksum(inout headers hdr, inout metadata meta) { apply { update_checksum(hdr.ipv4.isValid(), { hdr.ipv4.version, hdr.ipv4.ihl, hdr.ipv4.diffserv, hdr.ipv4.totalLen, hdr.ipv4.identification, hdr.ipv4.flags, hdr.ipv4.fragOffset, hdr.ipv4.ttl, hdr.ipv4.protocol, hdr.ipv4.srcAddr, hdr.ipv4.dstAddr }, hdr.ipv4.hdrChecksum, HashAlgorithm.csum16); } }
control MyDeparser(packet_out packet, in headers hdr) { apply { packet.emit(hdr.ethernet); packet.emit(hdr.ipv4); packet.emit(hdr.tcp); packet.emit(hdr.udp); } }
control MyVerifyChecksum(inout headers hdr, inout metadata meta) { apply { } }
V1Switch(MyParser(), MyVerifyChecksum(), MyIngress(), MyEgress(), MyComputeChecksum(), MyDeparser()) main;
    